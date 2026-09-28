"""Independent LLM judgments + explicit, uncalibrated propagation model."""
import asyncio
import json
import os
from datetime import datetime, timezone
from collections import Counter, defaultdict
from statistics import mean, pstdev
from . import store
from .media import extract, preview
from .providers import Provider, ProviderError
from .schemas import Profiles, Reaction, Analysis, Recommendations
from .network import initial_network, spread_targets, network_summary
from .agent_runtime import evaluate_persona
from .deep_analysis import recommend
from .skills import SkillRegistry

ARCHETYPES = ['High-intent buyer','Curious casual scroller','Skeptical industry expert','Existing customer','Creator likely to share useful content','Budget-conscious buyer','Trend-driven viewer (Gen Z only if audience fits)','Busy decision-maker','Research-oriented evaluator','Potential advocate']
SCORES = ['hookScore','retentionScore','clarityScore','relevanceScore','trustScore','shareIntent','saveIntent','commentIntent','clickIntent','conversionIntent','likeIntent','followIntent']

def aggregate(reactions, payload, evidence):
    if not reactions: raise ValueError('No valid persona responses. No outcome can be modeled.')
    metrics = {k:round(mean(r[k] for r in reactions),1) for k in SCORES}
    groups = defaultdict(list)
    for r in reactions: groups[r['personaType']].append(r)
    segments = [{'name':k,'count':len(rs),'relevance':round(mean(r['relevanceScore'] for r in rs),1),'share':round(mean(r['shareIntent'] for r in rs),1)} for k,rs in groups.items()]
    segments.sort(key=lambda s:s['relevance'],reverse=True)
    # Per-segment susceptibility incorporates every completed agent's stated response.
    # 0.06 is an EXPLICIT uncalibrated intent-to-behavior prior, NOT a learned probability.
    susceptibility = {k:mean((r['shareIntent']/100)*(r['relevanceScore']/100)*{'positive':1,'neutral':.65,'mixed':.75,'negative':.35}[r['sentiment']] for r in rs) for k,rs in groups.items()}
    weights = {k:len(rs)/len(reactions) for k,rs in groups.items()}
    current = {k:payload['seedReach']*weights[k] for k in groups}
    waves, edges = [], []
    for depth in range(4):
        waves.append({'label':['Initial seed reaction','First share wave','Secondary cluster response','Cascade slowing or growing'][depth], 'reach':round(sum(current.values())), 'clusters':{k:round(v,2) for k,v in current.items()}})
        nxt = {k:0.0 for k in groups}
        for origin, reach in current.items():
            generated = reach * susceptibility[origin] * .06 * payload['contactsPerShare'] * (.65 ** depth)
            for target in groups:
                # 65% within-interest affinity, 35% cross-cluster exposure.
                affinity = .65*(origin==target) + .35*weights[target]
                value = generated * affinity
                nxt[target] += value
                if depth<3: edges.append({'wave':depth+1,'from':origin,'to':target,'expectedExposures':round(value,3)})
        current = nxt
    total = sum(w['reach'] for w in waves)
    # Sensitivity envelope, explicitly not a statistical confidence interval.
    secondary = max(0,total-payload['seedReach'])
    low = round(payload['seedReach']*.6 + secondary*.3)
    high = round(payload['seedReach']*1.4 + secondary*2)
    engagement = mean(max(r['likeIntent'],r['saveIntent'],r['commentIntent'],r['shareIntent'],r['clickIntent'])/100 for r in reactions)*.12*100
    completion = len(reactions)/payload['size']
    evidence_score = (25 if evidence.get('metadata') else 0)+(30 if evidence.get('vision') else 0)+(25 if evidence.get('transcript') else 0)+(10 if evidence.get('caption') else 0)+(10 if evidence.get('oembed') else 0)
    confidence = min(75,round((15 + evidence_score*.6)*completion))
    verdict = 'Low relevance' if metrics['relevanceScore']<45 else 'Needs stronger hook' if metrics['hookScore']<55 else 'Strong niche hit' if min(metrics['hookScore'],metrics['relevanceScore'],metrics['shareIntent'])>=75 else 'Promising'
    return {'metrics':metrics,'verdict':verdict,'reachRange':[low,high],'engagementRate':round(engagement,2), 'cascadeDepth':sum(w['reach']>=1 for w in waves[1:]),'confidence':confidence,'waves':waves,'network':edges,'segments':segments,'sentiments':dict(Counter(r['sentiment'] for r in reactions)), 'emotions':dict(Counter(r['emotion'] for r in reactions)), 'completed':len(reactions),'requested':payload['size'], 'disagreement':round(pstdev(r['hookScore'] for r in reactions),1), 'assumptions':{'seedReach':payload['seedReach'],'contactsPerShare':payload['contactsPerShare'],'shareIntentRealization':0.06,'engagementIntentRealization':0.12,'waveDecay':0.65,'withinClusterAffinity':0.65,'reachRange':'Sensitivity envelope: seed × 0.6–1.4 plus modeled secondary exposure × 0.3–2.0. Not a statistical interval.','confidence':'Evidence/completion heuristic capped at 75; not probability of accuracy. More personas do not validate the model.','engagement':'Mean maximum engagement intent × 12% realization prior; uncalibrated scenario, not a platform forecast.','reach':'Exposure opportunities, not deduplicated unique viewers. No account analytics, ranking model or historical calibration.'}}

def checkpoint(directory, name, data):
    path = directory / name
    temporary = directory / (name+'.tmp')
    temporary.write_text(json.dumps(data),encoding='utf-8')
    temporary.replace(path)

def cached(directory,name):
    path = directory/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None

async def execute(id, semaphore):
    row = store.get(id)
    payload = row['payload']
    directory = store.MEDIA/id
    directory.mkdir(exist_ok=True, mode=0o700)
    prior_live = cached(directory,'live.json') or {}
    live = {'version':2,'nodes':[],'links':[],'events':[],'wave':0,'complete':False}
    provider = None
    def event(value):
        value = dict(value, seq=len(live['events']), at=datetime.now(timezone.utc).isoformat())
        live['events'].append(value)
        checkpoint(directory,'live.json',live)
    try:
        provider = Provider(payload['provider'])
        provider.events = event
        store.update(id,status='running',stage='Analyzing hook',progress=3,error=None)
        context = cached(directory,'context.json')
        if context is None:
            context = {'audience':payload['audience'],'angle':payload['angle'],'goal':payload['goal'],'platform':payload['platform'],'cta':payload['cta'],'caption':payload['caption'],'transcript':payload['transcript'],'limitations':[], 'evidence':{'caption':bool(payload['caption']),'transcript':bool(payload['transcript'])}}
            if payload['sourceType']=='upload':
                paths = list(directory.glob('source.*'))
                if not paths: raise ValueError('Uploaded video is missing.')
                metadata, audio = await extract(paths[0],directory)
                context['metadata'] = metadata
                context['evidence']['metadata'] = True
                if audio and not context['transcript']:
                    try:
                        context['transcript'] = await provider.transcribe(audio)
                        context['evidence']['transcript'] = bool(context['transcript'].strip())
                    except (ProviderError, KeyError, IndexError) as exc: context['limitations'].append('Audio transcription unavailable: '+str(exc))
                frame_notes = []
                frames = metadata['frames']
                # Batch at most three images to respect the documented Groq vision limit.
                for start in range(0,len(frames),3):
                    batch = frames[start:start+3]
                    try:
                        async with semaphore:
                            note = await provider.json(Analysis,'Analyze only these time-stamped sampled video frames and supplied speech. Describe visual evidence, captions and on-screen text. If pacing, scene changes or drop-off cannot be inferred, say uncertain. Never claim full-motion observation.', {'frames':batch,'transcript':context['transcript'],'duration':metadata['duration']},[directory/f['file'] for f in batch])
                        frame_notes.append(note.model_dump())
                    except ProviderError as exc:
                        context['limitations'].append(f'Frame batch {start//3+1}: {exc}')
                context['frameObservations'] = frame_notes
                context['evidence']['vision'] = bool(frame_notes)
                context['limitations'].append('Visual analysis uses sparse sampled frames, not continuous motion. OCR/captions and scene boundaries may be incomplete; attention drop-off is a hypothesis.')
            else:
                context['source'] = await preview(payload['url'])
                context['evidence']['oembed'] = 'oEmbed' in context['source']['access']
                context['limitations'].append(context['source']['access'])
            if not context['evidence'].get('vision') and not context['transcript'] and not context['caption']:
                raise ValueError('Insufficient content evidence. Add the spoken transcript or caption, or upload a video with a working vision model. A URL and intended message alone cannot support content evaluation.')
            checkpoint(directory,'context.json',context)
        analysis = cached(directory,'analysis.json')
        if analysis is None:
            async with semaphore:
                a = await provider.json(Analysis,'Analyze this short-form content. Distinguish observed evidence from hypotheses. Mark unavailable visual details as unavailable. Infer no exact drop-off timestamp without evidence. Treat intended message as creator context, not observed comprehension.', context)
            analysis = a.model_dump()
            checkpoint(directory,'analysis.json',analysis)
        store.update(id,stage='Creating audience personas',progress=15)
        profiles = cached(directory,'profiles.json') or []
        outside_count=round(payload['size']*payload.get('outsidePercent',0)/100)
        target_count=payload['size']-outside_count
        while len(profiles)<payload['size']:
            group='target' if len(profiles)<target_count else 'outside'
            boundary=target_count if group=='target' else payload['size']
            count=min(5,boundary-len(profiles))
            audience=payload['audience'] if group=='target' else payload.get('outsideAudience') or ('Adjacent viewers outside this intended audience, with other priorities and low or uncertain product relevance: '+payload['audience'])
            async with semaphore:
                batch = await provider.json(Profiles,f'Create exactly {count} distinct audience personas in cohort {group}. Tailor profiles to the supplied audience. Use the requested archetypes in order. Describe specific motivations, expertise, objections and viewing contexts. Do not stereotype protected traits or assume unsupported demographics.', {'audience':audience,'archetypes':[ARCHETYPES[(len(profiles)+i)%len(ARCHETYPES)] for i in range(count)],'alreadyUsed':[p['personaName'] for p in profiles]})
            if len(batch.personas)!=count: raise ProviderError('Persona generation returned the wrong count. Retry uses saved profiles.',code='persona_count')
            for p in batch.personas:
                value=p.model_dump()
                value['personaName']=f'{len(profiles)+1:03d} · {value["personaName"]}'
                value['personaType']=ARCHETYPES[len(profiles)%len(ARCHETYPES)]
                value['audienceGroup']=group
                profiles.append(value)
            checkpoint(directory,'profiles.json',profiles)
            # Show real generated profiles as they arrive; don't fabricate waiting identities.
            previous_events=live['events'];live=initial_network(profiles);live['events']=previous_events
            event({'kind':'profiles','message':f'{len(profiles)} / {payload["size"]} distinct profiles created.'})
            store.update(id,progress=15+round(10*len(profiles)/payload['size']))
        previous_events=live['events'];live=initial_network(profiles);live['events']=previous_events
        responses = cached(directory,'responses.json') or {}
        audits = cached(directory,'response-audit.json') or {}
        failures = {}
        previous_nodes={n['id']:n for n in prior_live.get('nodes',[])}
        for node in live['nodes']:
            key=node['id']
            if key in responses:
                old=previous_nodes.get(key,{})
                node.update(status='completed',reaction=responses[key],audit=audits.get(key,{'model':'legacy / not recorded'}),wave=old.get('wave'),parent=old.get('parent'),exposure=old.get('exposure','legacy'))
                event({'kind':'reused','nodeId':key,'wave':old.get('wave'),'exposure':old.get('exposure','legacy'),'message':node['profile']['personaName']+' · saved response restored'})
        abort=asyncio.Event()
        visited=set()
        store.update(id,stage='Collecting viewer reactions',progress=25)
        # Remove repeated per-frame analyses from every agent call; retain the full evidence synthesis.
        compact={'platform':payload['platform'],'goal':payload['goal'],'intendedMessage':payload['angle'],'cta':payload['cta'],'caption':context['caption'],'transcript':context['transcript'][:12000],'evidence':context['evidence'],'limitations':context['limitations']}
        if len(context['transcript'])>12000: compact['limitations']=compact['limitations']+['Transcript excerpt limited to 12000 characters; full analysis synthesis also supplied.']
        async def evaluate(id, wave, exposure, parent=None, strength=None):
            node=live['nodes'][int(id)];persona=profiles[int(id)]
            node.update(wave=wave,exposure=exposure,parent=parent,strength=strength)
            visited.add(id)
            if id in responses:
                node.update(status='completed',reaction=responses[id],audit=audits.get(id,{'model':'legacy / not recorded'}))
                event({'kind':'reused','nodeId':id,'wave':wave,'exposure':exposure,'parent':parent,'message':persona['personaName']+' · saved response reused'})
                return
            if abort.is_set():
                node['status']='paused'
                return
            node['status']='evaluating'
            event({'kind':'evaluating','nodeId':id,'wave':wave,'exposure':exposure,'parent':parent,'message':persona['personaName']+' is evaluating independently.'})
            try:
                async with semaphore:
                    # Independent inference context. No other viewer's reasoning or scores supplied.
                    def save_agent(value):
                        checkpoint(directory, f'agent-{id}.json', value)
                        node['agentExecution'] = {k:value[k] for k in ('runtime','phase','skills','evidence','steps')}
                    result, execution = await evaluate_persona(
                        provider, persona, compact, analysis,
                        state=cached(directory, f'agent-{id}.json'), save=save_agent,
                        emit=lambda value:event(dict(value, nodeId=id, wave=wave)))
                r=result.model_dump();r.update(personaName=persona['personaName'],personaType=persona['personaType'])
                responses[id]=r
                audits[id]={'provider':payload['provider'],'model':provider.model,'at':datetime.now(timezone.utc).isoformat(),**execution}
                checkpoint(directory,'responses.json',responses);checkpoint(directory,'response-audit.json',audits)
                node.update(status='completed',reaction=r,audit=audits[id])
                event({'kind':'reaction','nodeId':id,'wave':wave,'exposure':exposure,'parent':parent,'action':r['likelyAction'],'message':persona['personaName']+' → '+r['likelyAction']})
            except ProviderError as exc:
                failures[id]=exc.details();node.update(status='failed',error=exc.details())
                checkpoint(directory,'failures.json',failures)
                event({'kind':'failure','nodeId':id,'wave':wave,'message':str(exc),'code':exc.code})
                if exc.fatal or exc.status==429: abort.set()
            store.update(id=row['id'],progress=25+round(55*len(responses)/payload['size']),stage=f'Collecting viewer reactions · {len(responses)} / {payload["size"]} complete')
        async def batch(items,wave,exposure):
            queue=asyncio.Queue()
            for item in items: queue.put_nowait(item)
            async def worker():
                while not queue.empty() and not abort.is_set():
                    try: item=queue.get_nowait()
                    except asyncio.QueueEmpty: return
                    await evaluate(item[0],wave,exposure,item[1],item[2])
            await asyncio.gather(*(worker() for _ in range(max(1,min(10,int(os.getenv('AGENT_CONCURRENCY','1')))))))
        frontier=live['seedIds'];wave=0
        await batch([(x,None,None) for x in frontier],0,'seed')
        while frontier and wave<3 and not abort.is_set():
            next_nodes=spread_targets(live,frontier,visited)
            if not next_nodes: break
            wave+=1;live['wave']=wave
            event({'kind':'wave','wave':wave,'message':f'Share wave {wave}: {len(next_nodes)} newly exposed personas.'})
            await batch(next_nodes,wave,'share');frontier=[x[0] for x in next_nodes]
        # Unreached people still give independent control feedback, explicitly outside the cascade.
        if not abort.is_set():
            remaining=[(str(i),None,None) for i in range(len(profiles)) if str(i) not in visited]
            if remaining: event({'kind':'holdout','message':f'{len(remaining)} unreached viewers get a separate direct evaluation; excluded from cascade reach.'})
            await batch(remaining,None,'holdout')
        checkpoint(directory,'failures.json',failures)
        live['summary']=network_summary(live)
        checkpoint(directory,'live.json',live)
        if abort.is_set():
            problem=next(iter(failures.values()),{'message':'Provider requests paused.'})
            raise ProviderError(f'{len(responses)}/{payload["size"]} completed. Paused to avoid repeated failed calls. '+problem['message'])
        if len(responses)<max(5,payload['size']//2):
            counts=Counter(f['code'] for f in failures.values())
            detail='; '.join(f'{code}: {n}' for code,n in counts.items())
            raise ProviderError(f'Only {len(responses)}/{payload["size"]} completed. Failure breakdown: {detail}. Expand Agent errors for exact reasons. Successful responses are saved.')
        reactions=[responses[k] for k in sorted(responses,key=int)]
        store.update(id,stage='Modeling sharing cascade',progress=84)
        outcome = aggregate(reactions,payload,context['evidence'])
        store.update(id,stage='Generating recommendations',progress=90)
        rec = None
        recommendation_error = None
        recommendation_audit = None
        try:
            async with semaphore:
                # Reuse a completed report only for exactly the same completed panel.
                import hashlib
                panel_version = hashlib.sha256(json.dumps([responses,analysis,outcome['metrics'],
                    context['limitations'],provider.model,SkillRegistry().catalog('synthesis'),'deepagents-0.7.18'],
                    sort_keys=True).encode()).hexdigest()
                saved_report = cached(directory,'recommendations.json')
                if saved_report and saved_report.get('panelVersion') == panel_version:
                    rec = Recommendations.model_validate(saved_report['recommendations']).model_dump()
                    recommendation_audit = saved_report['audit']
                else:
                    brief = {'analysis':analysis,'metrics':outcome['metrics'],
                        'feedback':[{'id':key,'cohort':profiles[int(key)].get('audienceGroup','target'),
                            'type':r['personaType'],'objection':r['objection'][:350],
                            'edit':r['recommendedEdit'][:350],'understood':r['understood'][:250],
                            'sentiment':r['sentiment'],'action':r['likelyAction']}
                            for key,r in sorted(responses.items(),key=lambda item:int(item[0]))],
                        'limitations':context['limitations']+analysis['limitations']}
                    recommendation, recommendation_audit = await recommend(provider, brief,
                        save=lambda value:checkpoint(directory,'recommendation-audit.json',value), emit=event)
                    rec = recommendation.model_dump()
                    checkpoint(directory,'recommendations.json',{'panelVersion':panel_version,
                        'recommendations':rec,'audit':recommendation_audit})
        except ProviderError as exc: recommendation_error = str(exc)
        except Exception:
            # Do not discard valid viewer results or expose raw model/tool error bodies.
            recommendation_error = 'Deep analysis could not finish. Persona responses are saved; resume to retry the report.'
        result = {'analysis':analysis,'outcome':outcome,'recommendations':rec,'recommendationError':recommendation_error,'personas':reactions,'profiles':profiles,'failedAgents':failures,'evidence':context['evidence'],'limitations':context['limitations']+analysis['limitations'],'source':context.get('source'),'metadata':context.get('metadata'),'provider':payload['provider'],'model':provider.model,'networkSummary':network_summary(live),'responseAudit':audits,'disclaimer':'AI-modeled estimates. Not guaranteed platform performance or real historical analytics. Synthetic personas are not representative human research.'}
        result['recommendationAudit'] = recommendation_audit or cached(directory,'recommendation-audit.json')
        live['complete']=True
        live['summary']=network_summary(live)
        event({'kind':'complete','message':'Agent evaluation finished. Replay shows saved events, not new inference.'})
        store.update(id,status='partial' if failures or not rec else 'completed',stage='Complete',progress=100,result=result)
    except asyncio.CancelledError:
        store.update(id,status='interrupted',error='Server stopped; completed persona responses retained.')
        raise
    except (ProviderError, ValueError) as exc:
        event({'kind':'error','message':str(exc)})
        store.update(id,status='failed',stage='Needs attention',error=str(exc))
    except Exception:
        store.update(id,status='failed',stage='Needs attention',error='Unexpected processing failure. Check server logs; retry uses saved progress.')
        import logging
        logging.exception('Simulation %s failed',id)

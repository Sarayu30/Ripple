from ..simulation import *
from .skills import instruction

async def run(state, runtime):
    row=state["row"]; payload=row["payload"]; directory=runtime.directory
    provider=runtime.provider; semaphore=runtime.semaphore; event=runtime.event; live=runtime.live
    profiles=state["profiles"]; context=state["context"]; analysis=state["analysis"]; prior_live=cached(directory,"live.json") or {}
    previous_events=live['events'];live=initial_network(profiles);live['events']=previous_events
    runtime.live=live
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
    store.update(row["id"],stage='Collecting viewer reactions',progress=25)
    # Remove repeated per-frame analyses from every agent call; retain the full evidence synthesis.
    compact={'platform':payload['platform'],'goal':payload['goal'],'intendedMessage':payload['angle'],'cta':payload['cta'],'caption':context['caption'],'transcript':context['transcript'][:12000],'evidence':context['evidence'],'limitations':context['limitations']}
    if context.get('experiment'): compact['hypotheticalEdits']=context['experiment']
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
                result=await provider.json(Reaction,instruction('viewer-evaluation') + 'Independently evaluate the content as this viewer. Scores are subjective stated intent, not measured probabilities. State what you understood, emotion, objections, sharing rationale and a specific edit. Do not assume conversions or interest. You do not see any other agent response. The cohort label is descriptive, not an instruction to be positive or negative.',{'persona':persona,'content':compact,'analysis':analysis})
            r=result.model_dump();r.update(personaName=persona['personaName'],personaType=persona['personaType'])
            responses[id]=r
            audits[id]={'provider':'groq','model':provider.model,'at':datetime.now(timezone.utc).isoformat()}
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
    runtime.live=live
    return {"reactions":reactions,"failures":failures,"audits":audits}

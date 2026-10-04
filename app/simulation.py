"""Independent LLM judgments + explicit, uncalibrated propagation model."""
import json
from collections import Counter, defaultdict
from statistics import mean, pstdev
from .providers import Provider

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
    from .agents.orchestrator import execute_graph
    await execute_graph(id, semaphore, Provider)

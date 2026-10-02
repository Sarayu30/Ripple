"""Deterministic, auditable tools. These never make up model observations."""
from collections import Counter, defaultdict
from ..simulation import aggregate
from .skills import instruction

def evidence_catalog(context, reactions):
    evidence=[]
    for i, frame in enumerate(context.get('metadata',{}).get('frames',[])):
        evidence.append({'id':f'frame:{i}','kind':'video-observed source','description':f'Sampled frame at {frame["seconds"]}s. Visual descriptions are model interpretations.','file':frame['file']})
    if context.get('transcript'):
        evidence.append({'id':'transcript','kind':'transcript-derived','description':context['transcript']})
    if context.get('caption'):
        evidence.append({'id':'caption','kind':'creator-supplied','description':context['caption']})
    evidence.append({'id':'analysis','kind':'AI interpretation','description':'Content analysis inferred from available sources; not observed attention or behavior.'})
    if context.get('experiment'):
        evidence.append({'id':'experiment','kind':'hypothetical creator edit','description':str(context['experiment'])})
    evidence.extend({'id':f'viewer:{i}','kind':'synthetic reaction','description':r['personaName']+': '+r['objection']} for i,r in enumerate(reactions))
    evidence.append({'id':'propagation','kind':'mathematical assumption','description':'6% sharing realization prior; 0.65 wave decay; 65% within-cluster affinity. Uncalibrated exposure opportunities, not future unique reach.'})
    return evidence

async def propagation(state, runtime):
    # Loading the skill is part of execution and appears in the trace catalog.
    instruction('virality-analysis')
    result=aggregate(state['reactions'],state['row']['payload'],state['context']['evidence'])
    for segment in result['segments']:
        members=[r for r in state['reactions'] if r['personaType']==segment['name']]
        segment['dominantReaction']=Counter(r['likelyAction'] for r in members).most_common(1)[0][0]
        segment['insight']=Counter(r['objection'] for r in members).most_common(1)[0][0]
    return {'outcome':result,'provenance':evidence_catalog(state['context'],state['reactions'])}

def feedback(state):
    return [{'id':f'viewer:{i}','type':r['personaType'],'action':r['likelyAction'],'objection':r['objection'][:500],'edit':r['recommendedEdit'][:500],'understood':r['understood'][:300]} for i,r in enumerate(state['reactions'])]

def validate_sources(sources, evidence):
    allowed={e['id'] for e in evidence}
    if not sources or any(s not in allowed for s in sources):
        from ..providers import ProviderError
        raise ProviderError('Agent returned missing or unknown evidence references. Retry to regenerate.',code='invalid_evidence')

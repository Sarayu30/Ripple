from ..schemas import Insights
from ..simulation import checkpoint, cached
from .skills import instruction
from .analytics import feedback, validate_sources

async def run(state,runtime):
    saved=cached(runtime.directory,'insights.json')
    if saved:
        return {'insights':saved}
    async with runtime.semaphore:
        result=await runtime.provider.json(Insights,instruction('insight-synthesis'),{'feedback':feedback(state),'segments':state['outcome']['segments'],'evidenceIds':[e['id'] for e in state['provenance']]})
    for claim in result.patterns+result.disagreements:
        validate_sources(claim.sources,state['provenance'])
    value=result.model_dump()
    checkpoint(runtime.directory,'insights.json',value)
    return {'insights':value}

from ..schemas import Recommendations
from ..simulation import checkpoint, cached
from ..providers import ProviderError
from .skills import instruction
from .analytics import feedback, validate_sources

async def run(state,runtime):
    try:
        saved=cached(runtime.directory,'recommendations.json')
        if saved: return {'recommendations':saved,'recommendationError':None}
        async with runtime.semaphore:
            result=await runtime.provider.json(Recommendations,instruction('creative-optimization'),{'analysis':state['analysis'],'insights':state['insights'],'feedback':feedback(state),'evidenceIds':[e['id'] for e in state['provenance']],'limitations':state['context']['limitations']})
        validate_sources(result.sources,state['provenance'])
        value=result.model_dump()
        checkpoint(runtime.directory,'recommendations.json',value)
        return {'recommendations':value,'recommendationError':None}
    except ProviderError as exc:
        return {'recommendations':None,'recommendationError':str(exc)}

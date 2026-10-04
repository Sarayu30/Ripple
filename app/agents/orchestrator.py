"""Durable LangGraph workflow with explicit dependencies and restart recovery."""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from .. import store
from ..providers import ProviderError
from ..simulation import checkpoint, cached
from ..network import network_summary
from . import content, audience, viewers, insights, strategist
from .analytics import propagation
from .skills import catalog

class SimulationState(TypedDict, total=False):
    row: dict
    context: dict
    analysis: dict
    profiles: list
    reactions: list
    failures: dict
    audits: dict
    outcome: dict
    provenance: list
    insights: dict
    recommendations: dict | None
    recommendationError: str | None
    completed: bool

class Runtime:
    def __init__(self,id,semaphore,provider):
        self.id=id;self.directory=store.MEDIA/id;self.semaphore=semaphore;self.provider=provider
        self.live=cached(self.directory,'live.json') or {'version':2,'nodes':[],'links':[],'events':[],'wave':0,'complete':False}
        self.provider.events=self.event

    def event(self,value):
        self.live['events'].append(dict(value,seq=len(self.live['events']),at=datetime.now(timezone.utc).isoformat()))
        checkpoint(self.directory,'live.json',self.live)

def build_graph(runtime):
    graph=StateGraph(SimulationState)
    def wrap(name,fn,progress):
        async def node(state):
            store.update(runtime.id,stage=name.replace('_',' ').title(),progress=progress)
            runtime.event({'kind':'stage_start','agent':name,'message':name.replace('_',' ').title()+' started'})
            start=time.monotonic()
            try:
                output=await fn(state,runtime)
                runtime.event({'kind':'stage_complete','agent':name,'duration':round(time.monotonic()-start,2),'message':name.replace('_',' ').title()+' completed'})
                return output
            except Exception:
                runtime.event({'kind':'stage_failed','agent':name,'message':name.replace('_',' ').title()+' needs attention; saved stages retained'})
                raise
        return node
    stages=[('content_analysis',content.run,3),('audience_research',audience.run,15),('viewer_simulation',viewers.run,25),('propagation_analyst',propagation,84),('insights_analyst',insights.run,88),('creative_strategist',strategist.run,93)]
    for name,fn,progress in stages: graph.add_node(name,wrap(name,fn,progress))
    graph.add_edge(START,stages[0][0])
    for left,right in zip(stages,stages[1:]): graph.add_edge(left[0],right[0])
    async def finish(state):
        context=state['context'];live=runtime.live
        result={k:state[k] for k in ('analysis','outcome','recommendations','recommendationError','profiles','insights','provenance')}
        result.update(personas=state['reactions'],failedAgents=state['failures'],responseAudit=state['audits'],evidence=context['evidence'],limitations=context['limitations']+state['analysis']['limitations'],source=context.get('source'),metadata=context.get('metadata'),provider='groq',model=runtime.provider.model,networkSummary=network_summary(live),skills=catalog(),disclaimer='Exploratory AI simulation. Synthetic viewers are not human research; stated intent is not calibrated real-world probability.')
        live['complete']=True
        runtime.event({'kind':'complete','message':'Simulation complete. All results reference stored evidence.'})
        store.update(runtime.id,status='partial' if state['failures'] or not state['recommendations'] else 'completed',stage='Complete',progress=100,result=result)
        return {'completed':True}
    graph.add_node('save_results',finish)
    graph.add_edge(stages[-1][0],'save_results');graph.add_edge('save_results',END)
    return graph

async def execute_graph(id,semaphore,provider_factory):
    directory=store.MEDIA/id;directory.mkdir(exist_ok=True,mode=0o700)
    try:
        runtime=Runtime(id,semaphore,provider_factory('groq'))
        store.update(id,status='running',error=None)
        async with AsyncSqliteSaver.from_conn_string(str(directory/'workflow.sqlite')) as saver:
            graph=build_graph(runtime).compile(checkpointer=saver)
            config={'configurable':{'thread_id':id},'recursion_limit':30}
            snapshot=await graph.aget_state(config)
            # Interrupted/failed stages resume with the serialized upstream state.
            # Completed partial runs restart stage routing but reuse per-viewer caches.
            if snapshot.next:
                await graph.ainvoke(None,config)
            else:
                # Partial viewer recovery must refresh downstream insights.
                if snapshot.values.get('failures'):
                    for name in ('insights.json','recommendations.json'):
                        (directory/name).unlink(missing_ok=True)
                row=store.get(id)
                input_row={key:row[key] for key in ('id','title','created','payload')}
                await graph.ainvoke({'row':input_row,'completed':False},config)
    except asyncio.CancelledError:
        store.update(id,status='interrupted',error='Server stopped. Resume to use the saved workflow checkpoint.')
        raise
    except (ProviderError,ValueError) as exc:
        store.update(id,status='failed',stage='Needs attention',error=str(exc))
    except Exception:
        logging.exception('Simulation %s failed',id)
        store.update(id,status='failed',stage='Needs attention',error='Unexpected processing failure. Check server logs; retry uses saved progress.')

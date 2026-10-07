"""Real graph execution with test-only provider fixtures, never production demos."""
import asyncio
import uuid
import pytest
from fastapi.testclient import TestClient
from test_core import payload, reaction
from app import store, simulation
from app.main import app
from app.schemas import Analysis, Profiles, Reaction, Recommendations, Insights, ExperimentInput, ToolPlan, ChatAnswer
from app.providers import ProviderError
from app.experiments import create_version, compare
from app.agents.chat import answer
from app.agents.skills import catalog, instruction
from app.reports import creator_report

class FixtureProvider:
    calls=[]
    fail_insights=False
    def __init__(self,name='groq'): self.model='test-fixture'
    async def json(self,schema,prompt,data,images=None):
        self.calls.append((schema.__name__,data))
        if schema is Profiles:
            return Profiles(personas=[dict(personaName=f'Viewer {i}',personaType=k,background='Designer',motivation='Save time',skepticism='Proof',viewingContext='Lunch') for i,k in enumerate(data['archetypes'])])
        if schema is Analysis:
            return Analysis(**{k:'Based on supplied transcript' for k in ['summary','hook','dropOff','comprehension','ctaStrength','visualClarity','pacing','productVisibility','shareableMoment']},onScreenText=[],captions=[],scenes=[],limitations=['No frame evidence'])
        if schema is Reaction: return Reaction(**reaction())
        if schema is Insights:
            if self.fail_insights: raise ProviderError('Temporary insights failure')
            return Insights(summary='Show proof',patterns=[{'finding':'Proof helps','sources':['viewer:0']}],disagreements=[])
        if schema is Recommendations: return Recommendations(topEdits=['Show proof','Shorten hook','Clarify CTA'],alternativeHook='See this result',caption='Caption',cta='Save this',cover='Result',abVariants=['A','B'],keep=['Clarity'],sources=['viewer:0','analysis'])
        if schema is ToolPlan: return ToolPlan(tools=['simulation_results','segment_comparison'])
        if schema is ChatAnswer: return ChatAnswer(answer='Viewers want proof. Test a demonstrated result.',sources=['viewer:0'])
        raise AssertionError(schema)

def setup_run(monkeypatch):
    FixtureProvider.calls=[];FixtureProvider.fail_insights=False
    monkeypatch.setattr(simulation,'Provider',FixtureProvider)
    store.init();id=str(uuid.uuid4());store.create(id,payload())
    return id

def test_graph_restart_resumes_pending_stage(monkeypatch):
    id=setup_run(monkeypatch);FixtureProvider.fail_insights=True
    asyncio.run(simulation.execute(id,asyncio.Semaphore(2)))
    assert store.get(id)['status']=='failed'
    before=len([x for x in FixtureProvider.calls if x[0]=='Reaction'])
    assert before==25
    with store.db() as c:
        assert c.execute('SELECT 1 FROM checkpoints WHERE thread_id=%s', (id,)).fetchone()
    FixtureProvider.fail_insights=False
    asyncio.run(simulation.execute(id,asyncio.Semaphore(2)))
    row=store.get(id)
    assert row['status']=='completed'
    assert len([x for x in FixtureProvider.calls if x[0]=='Reaction'])==before
    assert len(row['result']['provenance'])>=27
    events=simulation.cached(store.MEDIA/id,'live.json')['events']
    assert len({x['agent'] for x in events if x['kind']=='stage_complete'})==6

def test_versions_invalidate_only_affected_work(monkeypatch):
    id=setup_run(monkeypatch);asyncio.run(simulation.execute(id,asyncio.Semaphore(2)))
    original=store.get(id)
    child=create_version(original,ExperimentInput(title='New hook',hook='Show the result first',approved=True))
    assert simulation.cached(store.MEDIA/child,'profiles.json')==original['result']['profiles']
    assert not (store.MEDIA/child/'analysis.json').exists()
    assert not (store.MEDIA/child/'responses.json').exists()
    FixtureProvider.calls=[];asyncio.run(simulation.execute(child,asyncio.Semaphore(2)))
    revised=store.get(child)
    assert revised['status']=='completed'
    assert not any(x[0]=='Profiles' for x in FixtureProvider.calls)
    assert all(x[1]['content']['hypotheticalEdits']['hook']=='Show the result first' for x in FixtureProvider.calls if x[0]=='Reaction')
    d=compare(original,revised)
    assert d['sharedPersonas'] and not d['assumptionDifferences']
    assert all(v==0 for v in d['metricDeltas'].values())
    assert 'Original recommendations' in creator_report(revised)
    audience=create_version(original,ExperimentInput(title='Different audience',audience='Experienced architects designing homes',approved=True))
    assert (store.MEDIA/audience/'analysis.json').exists()
    assert not (store.MEDIA/audience/'profiles.json').exists()
    FixtureProvider.calls=[];asyncio.run(simulation.execute(audience,asyncio.Semaphore(2)))
    assert not any(x[0]=='Analysis' for x in FixtureProvider.calls)
    assert any(x[0]=='Profiles' for x in FixtureProvider.calls)
    with TestClient(app) as client:
        versions=client.get('/api/tests/'+child+'/versions').json()
        assert {v['id'] for v in versions}=={id,child,audience}
        assert client.get('/api/tests/'+child+'/export').json()['version']['parentId']==id

def test_chat_uses_scoped_tools_and_persists_followups(monkeypatch):
    id=setup_run(monkeypatch);asyncio.run(simulation.execute(id,asyncio.Semaphore(2)))
    row=store.get(id)
    async def chat():
        first=await answer(row,'Why scroll?',FixtureProvider(),asyncio.Semaphore(1))
        assert first['sources']==['viewer:0']
        await answer(row,'Give me a hook for that',FixtureProvider(),asyncio.Semaphore(1))
    asyncio.run(chat())
    plans=[data for kind,data in FixtureProvider.calls if kind=='ToolPlan']
    assert len(plans[1]['history'])==2
    responses=[data for kind,data in FixtureProvider.calls if kind=='ChatAnswer']
    assert responses[0]['retrieved']['simulation_results']['viewers'][0]['objection']=='Needs proof'
    assert len(simulation.cached(store.MEDIA/id,'chat.json'))==4

def test_unknown_evidence_rejected():
    from app.agents.analytics import validate_sources
    with pytest.raises(ProviderError): validate_sources(['made-up'],[{'id':'analysis'}])
    with pytest.raises(ValueError): instruction('../../.env')
    assert len(catalog())==6


def test_chat_bounds_large_tools_and_long_followup_history(monkeypatch):
    from app.agents import chat
    id=setup_run(monkeypatch)
    asyncio.run(simulation.execute(id,asyncio.Semaphore(1)))
    simulation.checkpoint(store.MEDIA/id,'chat.json',[{'role':'user' if i%2==0 else 'assistant','text':'x'*4000} for i in range(20)])
    monkeypatch.setattr(chat,'retrieve',lambda name,row:{'longResult':'x'*50000})
    asyncio.run(answer(store.get(id),'Summarize the evidence',FixtureProvider(),asyncio.Semaphore(1)))
    context=next(data for kind,data in reversed(FixtureProvider.calls) if kind=='ChatAnswer')
    assert sum(len(m['text']) for m in context['history'])<=3000
    assert sum(len(v['excerpt']) for v in context['retrieved'].values())<=10000
    assert all(v['truncated'] for v in context['retrieved'].values())

def test_upgrade_api_contracts_and_approval(monkeypatch):
    id=setup_run(monkeypatch);asyncio.run(simulation.execute(id,asyncio.Semaphore(1)))
    with TestClient(app) as client:
        h={'X-Ripple-Client':'1'}
        assert client.post('/api/tests/'+id+'/versions',json={'title':'No approval','hook':'New'},headers=h).status_code==422
        report=client.get('/api/tests/'+id+'/report')
        assert report.status_code==200 and 'text/markdown' in report.headers['content-type']
        assert 'Synthetic viewers' in report.text
        assert client.get('/api/tests/'+id+'/chat').json()==[]
        assert client.post('/api/tests/'+id+'/chat',json={'message':'Hi'}).status_code==403
        assert client.get('/api/tests/'+id+'/compare/missing').status_code==404
        assert client.get('/api/tests/'+id+'/frames/..%2F.env').status_code==404

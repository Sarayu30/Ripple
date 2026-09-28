import asyncio
import json
import os
import tempfile
from pathlib import Path
import pytest
os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='ripple-test-')
os.environ.pop('APP_PASSWORD',None)
from fastapi.testclient import TestClient
from app.main import app
from app import store
from app.media import source_url, extract, run
from app.schemas import Reaction
from app.simulation import aggregate, execute
from app.providers import Provider, ProviderError


def reaction(score=65):
    data={k:score for k in ['hookScore','retentionScore','clarityScore','relevanceScore','trustScore','shareIntent','saveIntent','commentIntent','clickIntent','conversionIntent','likeIntent','followIntent']}
    data.update(personaName='Test viewer',personaType='Curious casual scroller',sentiment='positive',likelyAction='share',reaction='Useful explanation',objection='Needs proof',recommendedEdit='Show a real result',understood='A workflow',shareReason='Useful for my team',confusion='Unclear price',emotion='curiosity',wouldStop=True,wouldFinish=True)
    return data

def payload():
    return dict(title='Test A',audience='Independent designers seeking workflow tools',goal='engagement',angle='A faster design workflow',platform='Instagram',cta='Save this',size=25,sourceType='link',url='https://www.instagram.com/reel/example/',transcript='Here is a design workflow. First build your mood board.',caption='',seedReach=1000,contactsPerShare=8,provider='groq',consent=True)

@pytest.mark.parametrize('url',['http://example.com/x','https://localhost/x','https://127.0.0.1/x','https://10.0.0.2/x','https://example.com:8443/x','https://user:pass@example.com/x','file:///tmp/secret'])
def test_reject_bad_urls(url):
    with pytest.raises(ValueError): source_url(url)

def test_platform_host_boundary():
    assert source_url('https://instagram.com.attacker.com/reel/a')['platform']=='Other'
    assert source_url('https://www.instagram.com/reel/a')['platform']=='Instagram'

def test_schema_rejects_out_of_range_and_extra():
    r=reaction();r['hookScore']=101
    with pytest.raises(ValueError): Reaction.model_validate(r)
    r=reaction();r['secret']='injected'
    with pytest.raises(ValueError): Reaction.model_validate(r)

def test_cascade_uses_agent_intent_and_seed():
    p=payload()
    low=aggregate([reaction(0)]*25,p,{})
    high=aggregate([reaction(100)]*25,p,{'vision':True,'transcript':True})
    assert low['waves'][1]['reach']==0
    assert high['waves'][1]['reach']>0
    assert high['reachRange'][1]>low['reachRange'][1]
    assert high['confidence']<=75
    assert high['waves'][0]['reach']==1000
    assert high['engagementRate']==12
    assert low['verdict']=='Low relevance'
    assert aggregate([reaction()]*10,p,{})['confidence']<aggregate([reaction()]*25,p,{})['confidence']

def test_http_boundaries(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        assert 'default-src' in client.get('/').headers['content-security-policy']
        assert client.post('/api/preview',json={'url':'https://example.com'}).status_code==403
        assert client.post('/api/preview',json={'url':'https://example.com'},headers={'X-Ripple-Client':'1','Origin':'https://evil.example'}).status_code==403
        assert client.get('/data/ripple.sqlite3').status_code==404
        assert client.get('/api/tests/missing').status_code==404
        response=client.post('/api/tests',data={'payload':json.dumps(payload())},headers={'X-Ripple-Client':'1'})
        assert response.status_code==422
        assert 'GROQ_API_KEY' in response.json()['detail']
        assert 'GROQ_API_KEY' not in json.dumps(client.get('/api/config').json())
        monkeypatch.setenv('APP_PASSWORD','test-secret')
        assert client.get('/api/tests').status_code==401
        assert client.get('/api/tests',auth=('any','test-secret')).status_code==200

def test_real_ffmpeg_ingestion(tmp_path):
    async def check():
        video=tmp_path/'source.mp4'
        await run('ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=blue:s=320x240:d=4','-f','lavfi','-i','sine=frequency=440:duration=4','-c:v','mpeg4','-c:a','aac','-shortest',str(video))
        metadata,audio=await extract(video,tmp_path)
        assert 3.9<=metadata['duration']<=4.1
        assert len(metadata['frames'])>=4
        assert audio.exists()
        assert metadata['width']==320
    asyncio.run(check())

def test_independent_calls_checkpoint_retry(monkeypatch):
    """Fake provider is ONLY a test fixture. Production has no fake-results mode."""
    from app import simulation
    from app.schemas import Profiles, Analysis, Recommendations, AgentDecision
    calls=[]
    recommendation_calls=[]
    should_fail={'value':True}
    class FakeProvider:
        def __init__(self,name): self.model='test-model'
        async def json(self,schema,instruction,data,images=None):
            if schema is AgentDecision:
                if not data['loadedSkills']:
                    return AgentDecision(tool='load_skill',argument='attention-review')
                if len(data['observations'])==1:
                    return AgentDecision(tool='inspect_evidence',argument='transcript')
                return AgentDecision(tool='finish',argument='')
            if schema is Profiles:
                return Profiles(personas=[dict(personaName='Viewer '+str(i),personaType=k,background='Designer',motivation='Useful ideas',skepticism='Needs evidence',viewingContext='Busy lunch break') for i,k in enumerate(data['archetypes'])])
            if schema is Analysis:
                return Analysis(**{k:'Evidence-based test description' for k in ['summary','hook','dropOff','comprehension','ctaStrength','visualClarity','pacing','productVisibility','shareableMoment']},onScreenText=[],captions=[],scenes=[],limitations=['No visual evidence'])
            if schema is Reaction:
                assert 'feedback' not in data and 'reactions' not in data
                name=data['persona']['personaName'];calls.append(name)
                if should_fail['value'] and name.startswith('025'): raise ProviderError('Test quota failure')
                return Reaction(**reaction())
            return Recommendations(topEdits=['A','B','C'],alternativeHook='Hook',caption='Caption',cta='CTA',cover='Cover',abVariants=['A','B'],keep=['Clarity'])
    monkeypatch.setattr(simulation,'Provider',FakeProvider)
    async def fake_recommend(provider, data, **kwargs):
        recommendation_calls.append(data)
        result=Recommendations(topEdits=['A','B','C'],alternativeHook='Hook',caption='Caption',cta='CTA',cover='Cover',abVariants=['A','B'],keep=['Clarity'])
        return result, {'runtime':'test-fixture'}
    monkeypatch.setattr(simulation,'recommend',fake_recommend)
    async def check():
        id='pipeline-test'
        store.init();store.create(id,payload())
        await execute(id,asyncio.Semaphore(3))
        first=store.get(id)
        assert first['status']=='partial'
        assert len(first['result']['personas'])==24
        assert len(calls)==25 and len(set(calls))==25
        assert len(first['result']['failedAgents'])==1
        assert first['result']['responseAudit']['0']['runtime']=='skills-v1'
        should_fail['value']=False
        await execute(id,asyncio.Semaphore(3))
        final=store.get(id)
        assert final['status']=='completed'
        assert len(final['result']['personas'])==25
        assert len(calls)==26 # exactly one failed agent retried
        await execute(id,asyncio.Semaphore(3))
        assert len(calls)==26 and len(recommendation_calls)==2 # completed report reused
    asyncio.run(check())

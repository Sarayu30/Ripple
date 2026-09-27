"""v2 regression tests: topology, rate limits, structured responses and privacy."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi.testclient import TestClient
from app.providers import Provider, ProviderError, model_setting, retry_seconds, safe_schema
from app.network import initial_network, spread_targets, network_summary
from app.schemas import Reaction
from app.main import app
from app import store
from test_core import reaction, payload


def profiles(n=25):
    return [dict(personaName=f'Viewer {i}',personaType=['Buyer','Expert','Scroller'][i%3],audienceGroup='outside' if i>=20 else 'target',background='Background',motivation='Motivation',skepticism='Proof',viewingContext='Lunch') for i in range(n)]


def test_model_setting_rejects_common_paste_errors(monkeypatch):
    for bad in ('openai/gpt-oss-20b# comment','gsk_example_secret','   '):
        monkeypatch.setenv('GROQ_MODEL',bad)
        with pytest.raises(ProviderError) as exc: model_setting('GROQ_MODEL','default')
        assert bad not in str(exc.value) or bad=='   '


def test_schema_strict_and_retry_after():
    schema=safe_schema(Reaction.model_json_schema())
    assert set(schema['required'])==set(schema['properties'])
    assert schema['additionalProperties'] is False
    assert retry_seconds({'retry-after':'900'})==900 # long limit never silently shortened
    future=datetime.now(timezone.utc)+timedelta(seconds=120)
    assert 118<=retry_seconds({'retry-after':format_datetime(future)})<=121


def test_cascade_depends_on_returned_agents_and_never_double_counts():
    net=initial_network(profiles())
    seed=net['seedIds'][0];n=net['nodes'][int(seed)]
    n['reaction']=reaction(0)
    assert spread_targets(net,[seed],{seed})==[]
    n['reaction']=reaction(100)
    fresh=spread_targets(net,[seed],set(net['seedIds']))
    assert fresh and len(fresh)<=3
    assert not set(x[0] for x in fresh)&set(net['seedIds'])
    assert len(fresh)==len(set(x[0] for x in fresh))
    n.update(status='completed',exposure='seed',wave=0)
    for target,parent,strength in fresh:
        net['nodes'][int(target)].update(status='completed',reaction=reaction(),exposure='share',parent=parent,wave=1)
    holdout=next(x for x in net['nodes'] if x['reaction'] is None)
    holdout.update(status='completed',reaction=reaction(),exposure='holdout',wave=None)
    summary=network_summary(net)
    assert summary['completed']==len(fresh)+2
    assert summary['reached']==len(fresh)+1
    assert summary['cascadeDepth']==1
    assert summary['cohorts']['outside']['planned']==5
    assert sum(summary['waves'])==summary['reached']


def test_provider_errors_never_echo_secret_or_content(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','gsk_test_secret')
    monkeypatch.setenv('GROQ_MODEL','openai/gpt-oss-20b')
    p=Provider('groq')
    r=httpx.Response(404,json={'error':{'code':'model_not_found','message':'gsk_test_secret PRIVATE TRANSCRIPT'}})
    exc=p.error(r,p.model)
    assert exc.status==404 and exc.fatal
    assert 'model_not_found' in str(exc) and 'openai/gpt-oss-20b' in str(exc)
    assert 'gsk_' not in str(exc) and 'PRIVATE' not in str(exc)


def test_real_adapter_structured_schema_and_validation_repair(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','gsk_test_only')
    monkeypatch.setenv('GROQ_MODEL','openai/gpt-oss-20b')
    monkeypatch.setenv('REQUEST_INTERVAL_SECONDS','0')
    monkeypatch.setenv('MAX_PROVIDER_ATTEMPTS','2')
    bodies=[]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,**kw):
            bodies.append(kw['json']);r=reaction()
            if len(bodies)==1: r['hookScore']=101
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(r)}}]})
    monkeypatch.setattr('app.providers.httpx.AsyncClient',lambda **kw:Client())
    monkeypatch.setattr('app.providers.asyncio.sleep',AsyncMock())
    result=asyncio.run(Provider('groq').json(Reaction,'Assess honestly',{'content':'Test'}))
    assert result.hookScore==65
    assert len(bodies)==2
    assert bodies[0]['response_format']['json_schema']['strict'] is True
    assert bodies[0]['reasoning_effort']=='low'
    assert 'hookScore' in bodies[1]['messages'][0]['content']


def test_long_quota_reset_stops_instead_of_burning_calls(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','gsk_other_test')
    monkeypatch.setenv('REQUEST_INTERVAL_SECONDS','0')
    calls=[]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kw):
            calls.append(1)
            return httpx.Response(429,headers={'retry-after':'3600'},json={'error':{'code':'rate_limit_exceeded'}})
    monkeypatch.setattr('app.providers.httpx.AsyncClient',lambda **kw:Client())
    with pytest.raises(ProviderError) as exc: asyncio.run(Provider('groq').json(Reaction,'Assess',{}))
    assert len(calls)==1 and exc.value.retry_after==3600 and exc.value.fatal


def test_legacy_results_can_open_and_export_without_inventing_cascade():
    from app.simulation import checkpoint
    import uuid
    id=str(uuid.uuid4())
    with TestClient(app) as client:
        store.create(id,payload());directory=store.MEDIA/id;directory.mkdir()
        checkpoint(directory,'profiles.json',profiles(2));checkpoint(directory,'responses.json',{'0':reaction()})
        store.update(id,status='completed')
        live=client.get('/api/tests/'+id+'/live').json()
        assert live['legacy'] and live['nodes'][0]['exposure']=='legacy'
        assert live['summary']['reached']==0
        assert live['summary']['completed']==1
        assert client.get('/api/tests/'+id+'/export').json()['liveNetwork']['legacy']
        assert client.get('/api/tests/'+id+'/video').status_code==404

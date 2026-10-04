"""Citation compatibility and recovery for pre-upgrade Ask Ripple results."""
import asyncio
from copy import deepcopy
import pytest
from test_upgrade import setup_run, FixtureProvider
from app import simulation, store
from app.agents.chat import answer
from app.agents.tools import simulation_evidence, retrieve
from app.providers import ProviderError
from app.schemas import ChatAnswer

def legacy_run(monkeypatch):
    id=setup_run(monkeypatch)
    asyncio.run(simulation.execute(id,asyncio.Semaphore(1)))
    row=store.get(id)
    row['result'].pop('provenance')
    row['result'].pop('insights')
    return row

def test_legacy_retrieved_viewers_are_valid_citations(monkeypatch):
    row=legacy_run(monkeypatch)
    original=deepcopy(row)
    catalog={e['id'] for e in simulation_evidence(row)}
    viewers=retrieve('simulation_results',row)['viewers']
    assert {v['id'] for v in viewers}<=catalog
    assert 'viewer:25' not in catalog
    result=asyncio.run(answer(row,'Why are viewers scrolling?',FixtureProvider(),asyncio.Semaphore(1)))
    assert result['sources']==['viewer:0']
    assert row==original
    assert len(simulation.cached(store.MEDIA/row['id'],'chat.json'))==2

def test_invalid_citation_retries_without_replanning_or_saving_bad_reply(monkeypatch):
    row=legacy_run(monkeypatch)
    class RepairProvider(FixtureProvider):
        attempts=0
        plans=0
        async def json(self,schema,prompt,data,images=None):
            if schema is ChatAnswer:
                self.attempts+=1
                if self.attempts==1:
                    assert 'tool:version_comparison' not in data['evidenceIds']
                    return ChatAnswer(answer='Unverified answer',sources=['viewer:999'])
                assert 'citationCorrection' in data
                assert 'viewer:0' in data['evidenceIds']
                return ChatAnswer(answer='A verified answer',sources=['viewer:0'])
            self.plans+=1
            return await super().json(schema,prompt,data,images)
    provider=RepairProvider()
    result=asyncio.run(answer(row,'Why scroll?',provider,asyncio.Semaphore(1)))
    assert result['answer']=='A verified answer'
    assert provider.attempts==2 and provider.plans==1
    history=simulation.cached(store.MEDIA/row['id'],'chat.json')
    assert len(history)==2 and history[-1]['text']=='A verified answer'

def test_repeated_unknown_sources_fail_safely_without_changing_history(monkeypatch):
    row=legacy_run(monkeypatch)
    before=[{'role':'user','text':'Previous question'},{'role':'assistant','text':'Previous answer'}]
    simulation.checkpoint(store.MEDIA/row['id'],'chat.json',before)
    class InvalidProvider(FixtureProvider):
        attempts=0
        async def json(self,schema,prompt,data,images=None):
            if schema is ChatAnswer:
                self.attempts+=1
                return ChatAnswer(answer='Cannot be verified',sources=['not-a-source'])
            return await super().json(schema,prompt,data,images)
    provider=InvalidProvider()
    with pytest.raises(ProviderError,match='after retrying'):
        asyncio.run(answer(row,'Why scroll?',provider,asyncio.Semaphore(1)))
    assert provider.attempts==2
    assert simulation.cached(store.MEDIA/row['id'],'chat.json')==before

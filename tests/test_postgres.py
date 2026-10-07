import json
import sqlite3
import uuid
from contextlib import closing
import pytest
from app import store

def test_import_preserves_data_and_does_not_resurrect_deletion(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    id = str(uuid.uuid4())
    payload = {'title': 'Original ü', 'audience': 'Existing audience'}
    result = {'personas': [], 'unchanged': True}
    with closing(sqlite3.connect(path)) as old:
        old.execute('CREATE TABLE tests (id TEXT,created TEXT,title TEXT,status TEXT,stage TEXT,progress INTEGER,payload TEXT,result TEXT,error TEXT)')
        old.execute('INSERT INTO tests VALUES (?,?,?,?,?,?,?,?,?)', (id,'2026-01-01',payload['title'],'completed','Complete',100,json.dumps(payload),json.dumps(result),None))
        old.commit()
    before = path.read_bytes()
    with store.db() as c:
        assert store.import_legacy(c, path) == 1
    assert store.get(id)['payload'] == payload
    assert store.get(id)['result'] == result
    store.delete(id)
    with store.db() as c:
        assert store.import_legacy(c, path) == 0
    assert store.get(id) is None
    assert path.read_bytes() == before

def test_rollback_and_update_allowlist():
    id = str(uuid.uuid4())
    with pytest.raises(RuntimeError):
        with store.db() as c:
            c.execute('INSERT INTO tests (id,title) VALUES (%s,%s)', (id,'Rolled back'))
            raise RuntimeError('rollback')
    assert store.get(id) is None
    with pytest.raises(ValueError):
        store.update(id, payload='not allowed')

def test_schema_rejects_sql(monkeypatch):
    monkeypatch.setenv('DATABASE_SCHEMA', 'public; DROP TABLE tests')
    with pytest.raises(RuntimeError):
        store.schema()

def test_history_shows_actual_audience_and_verdict():
    id = str(uuid.uuid4())
    store.create(id, {'title': 'History summary', 'audience': 'Existing audience'})
    store.update(id, result={'outcome': {'verdict': 'Actual stored verdict'}})
    summary = next(row for row in store.listing() if row['id'] == id)
    assert summary['audience'] == 'Existing audience'
    assert summary['verdict'] == 'Actual stored verdict'
    assert 'payload' not in summary and 'result' not in summary
    store.delete(id)

def test_legacy_workflow_checkpoint_resumes_without_repeating_viewers(monkeypatch):
    import asyncio
    from app import simulation
    from test_upgrade import setup_run, FixtureProvider
    id = setup_run(monkeypatch)
    directory = store.MEDIA / id
    directory.mkdir(parents=True, exist_ok=True)
    # A pre-existing SQLite checkpoint selects the compatibility saver.
    with closing(sqlite3.connect(directory / 'workflow.sqlite')):
        pass
    FixtureProvider.fail_insights = True
    asyncio.run(simulation.execute(id, asyncio.Semaphore(2)))
    assert store.get(id)['status'] == 'failed'
    calls = len([entry for entry in FixtureProvider.calls if entry[0] == 'Reaction'])
    assert calls == 25
    FixtureProvider.fail_insights = False
    asyncio.run(simulation.execute(id, asyncio.Semaphore(2)))
    assert store.get(id)['status'] == 'completed'
    assert len([entry for entry in FixtureProvider.calls if entry[0] == 'Reaction']) == calls
    with store.db() as c:
        assert not c.execute('SELECT 1 FROM checkpoints WHERE thread_id=%s', (id,)).fetchone()
    assert (directory / 'workflow.sqlite').exists()

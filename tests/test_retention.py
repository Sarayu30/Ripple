"""Loss of temporary disk must not lose saved research or expose media."""
import asyncio
import json
import shutil
import uuid
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app import auth, store, simulation, worker
from app.agents import content
from app.main import app
from app.retention import purge_media, needs_upload, sweep
from test_core import payload
from test_upgrade import FixtureProvider


def new_run(**overrides):
    identifier = str(uuid.uuid4())
    store.create(identifier, dict(payload(), **overrides))
    directory = store.MEDIA / identifier
    directory.mkdir()
    return identifier, directory


def test_text_state_survives_disk_loss_and_is_owner_scoped():
    identifier, directory = new_run()
    for name in ('chat.json', 'live.json', 'experiment.json', 'context.json'):
        simulation.checkpoint(directory, name, {'saved': name})
    shutil.rmtree(directory)
    store.close()
    assert simulation.cached(directory, 'chat.json') == {'saved': 'chat.json'}
    token = auth.identity.set('different-account')
    try:
        assert simulation.cached(directory, 'chat.json') is None
        with pytest.raises(ValueError):
            simulation.checkpoint(directory, 'chat.json', {'overwritten': True})
    finally:
        auth.identity.reset(token)
    assert simulation.cached(directory, 'experiment.json') == {'saved': 'experiment.json'}
    store.delete(identifier)
    with store.db() as c:
        assert not c.execute('SELECT 1 FROM run_artifacts WHERE run_id=%s', (identifier,)).fetchone()


def test_content_removes_media_after_saving_observations(monkeypatch):
    identifier, directory = new_run(sourceType='upload')
    (directory/'source.mp4').write_bytes(b'test video')
    async def extract(path, target):
        (target/'frame-0.jpg').write_bytes(b'test frame')
        (target/'audio.wav').write_bytes(b'test audio')
        return {'duration': 3, 'frames': [{'file':'frame-0.jpg','seconds':0}]}, target/'audio.wav'
    monkeypatch.setattr(content, 'extract', extract)
    runtime = SimpleNamespace(directory=directory, provider=FixtureProvider(),
                              semaphore=asyncio.Semaphore(1), event=lambda e: None, live={})
    state = asyncio.run(content.run({'row':store.get(identifier)}, runtime))
    assert state['context']['evidence']['vision']
    assert simulation.cached(directory,'context.json')['frameObservations']
    assert not list(directory.iterdir())
    assert not needs_upload(store.get(identifier))
    # Running content again must use persisted observations without needing media.
    asyncio.run(content.run({'row':store.get(identifier)}, runtime))
    store.delete(identifier)


def test_failure_and_cancelled_queue_remove_media(monkeypatch):
    identifier, directory = new_run(sourceType='upload')
    (directory/'source.mp4').write_bytes(b'invalid')
    async def fail(path, target):
        (target/'frame-0.jpg').write_bytes(b'partial')
        raise ValueError('Invalid test video')
    monkeypatch.setattr(content, 'extract', fail)
    monkeypatch.setattr(simulation, 'Provider', FixtureProvider)
    asyncio.run(simulation.execute(identifier, asyncio.Semaphore(1)))
    assert store.get(identifier)['status'] == 'failed'
    assert not list(directory.iterdir())
    assert needs_upload(store.get(identifier))
    store.delete(identifier)
    with TestClient(app) as client:
        identifier, directory = new_run(sourceType='upload')
        (directory/'source.mp4').write_bytes(b'queued')
        response = client.post('/api/tests/'+identifier+'/cancel', headers={'X-Ripple-Client':'1'})
        assert response.status_code == 200
        assert not list(directory.iterdir())
        assert client.post('/api/tests/'+identifier+'/retry', headers={'X-Ripple-Client':'1'}).status_code == 409
        store.delete(identifier)


def test_recovery_distinguishes_missing_upload_from_saved_analysis():
    missing, directory = new_run(sourceType='upload')
    saved, saved_directory = new_run(sourceType='upload')
    simulation.checkpoint(saved_directory, 'context.json', {'frameObservations':['saved text']})
    store.update(missing,status='running')
    store.update(saved,status='running')
    worker.recover()
    assert store.get(missing)['status'] == 'failed'
    assert 'upload the video again' in store.get(missing)['error']
    assert store.get(saved)['status'] == 'queued'
    store.delete(missing)
    store.delete(saved)


def test_legacy_text_migration_and_media_sweep():
    identifier, directory = new_run()
    (directory/'chat.json').write_text(json.dumps([{'text':'saved conversation'}]))
    (directory/'source.mp4').write_bytes(b'old media')
    store.update(identifier,status='completed')
    from app.retention import migrate_legacy_text
    migrate_legacy_text()
    sweep()
    assert not (directory/'source.mp4').exists()
    shutil.rmtree(directory)
    assert simulation.cached(directory,'chat.json') == [{'text':'saved conversation'}]
    store.delete(identifier)

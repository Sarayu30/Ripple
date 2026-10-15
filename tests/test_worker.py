import uuid
import pytest
from app import auth, store, worker


def test_exclusive_backend_and_safe_recovery():
    connection = worker.acquire()
    try:
        with pytest.raises(RuntimeError, match='Another Ripple backend'):
            worker.acquire()
        identifier = str(uuid.uuid4())
        store.create(identifier, {'title': 'Recover me'})
        store.update(identifier, status='running')
        # Schema initialization must not interrupt another process's jobs.
        store.init()
        assert store.get(identifier)['status'] == 'running'
        worker.recover()
        assert store.get(identifier)['status'] == 'queued'
        assert any(row['id'] == identifier and row['owner_id'] == auth.owner() for row in worker.pending(100))
        store.delete(identifier)
    finally:
        connection.close()

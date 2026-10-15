import uuid
from app import auth, store


def test_all_storage_access_scoped_to_owner():
    identifier = str(uuid.uuid4())
    token = auth.identity.set('alice')
    try:
        store.create(identifier, {'title': 'Private Alice project', 'audience': 'Private audience'})
        assert store.get(identifier)
        auth.identity.set('bob')
        assert store.get(identifier) is None
        assert identifier not in {row['id'] for row in store.listing()}
        store.update(identifier, status='failed')
        store.delete(identifier)
        auth.identity.set('alice')
        assert store.get(identifier)['status'] == 'queued'
        store.delete(identifier)
    finally:
        auth.identity.reset(token)

import uuid
import time
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from unittest.mock import Mock
from fastapi.testclient import TestClient
from app import auth, store
from app.main import app


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


def test_neon_api_isolation_cookie_and_logout(monkeypatch):
    key = ed25519.Ed25519PrivateKey.generate()
    monkeypatch.setenv('AUTH_MODE', 'neon')
    monkeypatch.setenv('NEON_AUTH_BASE_URL', 'https://fixture.neon.tech/auth/auth')
    monkeypatch.setattr(auth, 'jwks_client', Mock(return_value=Mock(
        get_signing_key_from_jwt=Mock(return_value=Mock(key=key.public_key())))))
    alice, bob, identifier = (str(uuid.uuid4()) for _ in range(3))
    def bearer(user):
        token = jwt.encode(dict(iss='https://fixture.neon.tech', sub=user,
            exp=int(time.time())+60, iat=int(time.time()), emailVerified=True, banned=False,
            aud='https://fixture.neon.tech', role='authenticated'), key, algorithm='EdDSA')
        return {'Authorization': 'Bearer ' + token, 'X-Ripple-Client': '1'}
    context = auth.identity.set(alice)
    try:
        with TestClient(app) as client:
            store.create(identifier, {'title': 'Private', 'audience': 'Private'})
            assert client.get('/api/tests').status_code == 401
            response = client.post('/api/auth/session', headers=bearer(alice))
            assert response.status_code == 200
            assert 'HttpOnly' in response.headers['set-cookie']
            assert client.get('/api/tests/'+identifier).status_code == 200
            for suffix in ['', '/video', '/frames/frame-0.jpg', '/export', '/live', '/versions', '/chat', '/report', '/compare/'+identifier]:
                assert client.get('/api/tests/'+identifier+suffix, headers=bearer(bob)).status_code == 404
            assert client.delete('/api/tests/'+identifier, headers=bearer(bob)).status_code == 404
            assert client.post('/api/tests/'+identifier+'/retry', headers=bearer(bob)).status_code == 404
            assert client.post('/api/tests/'+identifier+'/chat', json={'message': 'Explain this'}, headers=bearer(bob)).status_code == 404
            assert client.post('/api/auth/logout', headers={'X-Ripple-Client':'1'}).status_code == 200
            assert client.get('/api/tests').status_code == 401
            assert store.get(identifier)
            store.delete(identifier)
    finally:
        auth.identity.reset(context)

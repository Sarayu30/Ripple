import uuid
import time
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
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


def test_supabase_api_isolation_cookie_and_logout(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv('AUTH_MODE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://fixture.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_' + 'x' * 32)
    monkeypatch.setenv('SUPABASE_JWT_PUBLIC_KEY', public)
    alice, bob, identifier = (str(uuid.uuid4()) for _ in range(3))
    def bearer(user):
        token = jwt.encode(dict(iss='https://fixture.supabase.co/auth/v1', sub=user,
            session_id=str(uuid.uuid4()), exp=int(time.time())+60, iat=int(time.time()),
            aud='authenticated', role='authenticated'), key, algorithm='ES256')
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

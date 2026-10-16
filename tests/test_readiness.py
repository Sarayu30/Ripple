from fastapi.testclient import TestClient
from app.main import app
from app import settings


def test_host_probe_does_not_open_application_api(monkeypatch):
    # Configure production routing after lifespan validation to focus this test
    # on the anonymous probe boundary, without production storage/configuration.
    with TestClient(app) as client:
        monkeypatch.setattr(settings, 'production', lambda: True)
        monkeypatch.setenv('ORIGIN_SECRET', 'test-origin-only-' * 4)
        monkeypatch.setenv('AUTH_MODE', 'neon')
        monkeypatch.setenv('NEON_AUTH_BASE_URL', 'https://fixture.neon.tech/auth/auth')
        response = client.get('/healthz')
        assert response.status_code in (200, 503)
        assert set(response.json()) == {'status'}
        assert 'no-store' in response.headers['cache-control']
        assert client.get('/api/tests').status_code == 403
        assert client.get('/api/config').status_code == 403
        assert client.post('/healthz').status_code == 403
        assert client.get('/api/tests', headers={'x-ripple-origin-secret':'test-origin-only-' * 4}).status_code == 401

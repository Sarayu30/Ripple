import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import store
from app.main import app


def test_cancel_and_retryable_deletion():
    with TestClient(app) as client:
        identifier=str(uuid.uuid4())
        store.create(identifier, {'title':'Cancel this', 'sourceType':'link'})
        headers={'X-Ripple-Client':'1'}
        assert client.delete('/api/tests/'+identifier,headers=headers).status_code==409
        assert client.post('/api/tests/'+identifier+'/cancel',headers=headers).status_code==200
        assert store.get(identifier)['status']=='cancelled'
        directory=store.MEDIA/identifier
        directory.mkdir()
        with patch('app.main.shutil.rmtree',side_effect=OSError('private-path-canary')):
            response=client.delete('/api/tests/'+identifier,headers=headers)
        assert response.status_code==503
        assert 'private-path-canary' not in response.text
        assert store.get(identifier)['status']=='deleting'
        assert client.delete('/api/tests/'+identifier,headers=headers).status_code==200
        assert not directory.exists() and store.get(identifier) is None

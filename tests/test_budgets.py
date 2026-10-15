import uuid
import pytest
from fastapi import HTTPException
from app import auth, budgets, store


def test_duplicate_submission_and_deleted_usage(monkeypatch):
    token = auth.identity.set(str(uuid.uuid4()))
    monkeypatch.setenv('DAILY_VIEWER_BUDGET', '25')
    identifier, retry = str(uuid.uuid4()), str(uuid.uuid4())
    key = uuid.uuid4().hex
    payload = {'title': 'One request', 'size': 25}
    try:
        assert budgets.admit(identifier, payload, key, 'media') == identifier
        assert budgets.admit(retry, payload, key, 'media') == identifier
        assert store.get(retry) is None
        with pytest.raises(HTTPException) as conflict:
            budgets.admit(retry, payload, key, 'changed-media')
        assert conflict.value.status_code == 409
        store.delete(identifier)
        with pytest.raises(HTTPException) as limited:
            budgets.admit(retry, payload)
        assert limited.value.status_code == 429
    finally: auth.identity.reset(token)

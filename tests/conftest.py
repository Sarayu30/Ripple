"""Integration tests use a unique PostgreSQL schema, never production records."""
import os
import tempfile
import uuid
from pathlib import Path
from dotenv import load_dotenv
import pytest

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
_test_schema = 'ripple_test_' + uuid.uuid4().hex
os.environ['DATABASE_SCHEMA'] = _test_schema
# Set this before collection imports app.store, even when running one test file.
_artifacts = Path(__file__).resolve().parents[1] / 'artifacts'
_artifacts.mkdir(exist_ok=True)
os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='test-data-', dir=_artifacts)

@pytest.fixture(scope='session', autouse=True)
def isolated_database():
    import psycopg
    from psycopg import sql
    from app import store
    store.init()
    yield
    store.close()
    assert store.schema() == _test_schema and _test_schema.startswith('ripple_test_')
    with psycopg.connect(store.database_url(), autocommit=True) as connection:
        connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(_test_schema)))

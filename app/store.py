"""PostgreSQL workspace storage with a non-destructive legacy SQLite import."""
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

ROOT = Path(os.getenv('DATA_DIR', './data')).resolve()
ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
MEDIA = ROOT / 'private'
MEDIA.mkdir(exist_ok=True, mode=0o700)
_pool = None
_pool_key = None

def database_url():
    value = os.getenv('DATABASE_URL', '').strip()
    if not value.startswith(('postgresql://', 'postgres://')):
        raise RuntimeError('Set DATABASE_URL to your PostgreSQL connection URL in .env.')
    # Neon transaction pooling rejects startup search_path; use the same endpoint's
    # direct hostname with our bounded application pool and session checkpoints.
    parts = urlsplit(value)
    if parts.hostname and parts.hostname.endswith('.neon.tech') and '-pooler.' in parts.hostname:
        value = urlunsplit(parts._replace(netloc=parts.netloc.replace(parts.hostname, parts.hostname.replace('-pooler.', '.'))))
    return value

def schema():
    value = os.getenv('DATABASE_SCHEMA', 'ripple')
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', value):
        raise RuntimeError('DATABASE_SCHEMA must be a lowercase PostgreSQL identifier.')
    return value

def connection_options():
    return dict(row_factory=dict_row, prepare_threshold=None, connect_timeout=15,
                options='-c search_path=' + schema())

@contextmanager
def db():
    global _pool, _pool_key
    key = (database_url(), schema())
    if _pool is None or _pool_key != key:
        close()
        _pool = ConnectionPool(key[0], kwargs=connection_options(), min_size=1,
                               max_size=6, timeout=20, open=True)
        _pool_key = key
    with _pool.connection() as connection:
        yield connection

def close():
    global _pool, _pool_key
    if _pool is not None:
        _pool.close()
    _pool = _pool_key = None

def import_legacy(connection, path=None):
    """Import once in the caller's transaction; leave the source untouched."""
    path = Path(path or ROOT / 'ripple.sqlite3').resolve()
    if not path.is_file():
        return 0
    key = 'sqlite:' + hashlib.sha256(str(path).encode()).hexdigest()
    connection.execute('SELECT pg_advisory_xact_lock(72419703)')
    if connection.execute('SELECT 1 FROM migrations WHERE name=%s', (key,)).fetchone():
        return 0
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as old:
        old.row_factory = sqlite3.Row
        rows = old.execute('SELECT * FROM tests').fetchall()
    for row in rows:
        values = dict(row)
        for field in ('payload', 'result'):
            if values[field]:
                json.loads(values[field])
        existing = connection.execute('SELECT * FROM tests WHERE id=%s', (row['id'],)).fetchone()
        if existing:
            if any(existing[k] != values[k] for k in values):
                raise RuntimeError('Legacy import found a conflicting simulation ID; source retained.')
            continue
        connection.execute('INSERT INTO tests (id,created,title,status,stage,progress,payload,result,error) '
                           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                           [values[k] for k in ('id','created','title','status','stage','progress','payload','result','error')])
    connection.execute('INSERT INTO migrations (name) VALUES (%s)', (key,))
    return len(rows)

def init():
    with psycopg.connect(database_url(), autocommit=True, **connection_options()) as c:
        c.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema())))
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS tests (id TEXT PRIMARY KEY, created TEXT, title TEXT, '
                  'status TEXT, stage TEXT, progress INTEGER, payload TEXT, result TEXT, error TEXT)')
        c.execute('CREATE INDEX IF NOT EXISTS tests_created_idx ON tests (created DESC)')
        c.execute('CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY, applied TIMESTAMPTZ DEFAULT now())')
        import_legacy(c)
        c.execute("UPDATE tests SET status='interrupted', error='Server restarted. Resume to reuse completed viewer evaluations.' WHERE status IN ('queued','running')")
    from .checkpoints import setup
    setup()

def create(id, payload):
    with db() as c:
        c.execute('INSERT INTO tests VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                  (id, datetime.now(timezone.utc).isoformat(), payload['title'], 'queued', 'Queued', 0, json.dumps(payload), None, None))

def update(id, **fields):
    allowed = {'status', 'stage', 'progress', 'result', 'error'}
    if not fields or not set(fields) <= allowed:
        raise ValueError('Unsupported simulation update')
    if 'result' in fields:
        fields['result'] = json.dumps(fields['result'])
    with db() as c:
        c.execute('UPDATE tests SET ' + ','.join(f'{k}=%s' for k in fields) + ' WHERE id=%s', [*fields.values(), id])

def get(id):
    with db() as c:
        row = c.execute('SELECT * FROM tests WHERE id=%s', (id,)).fetchone()
    if row:
        for key in ('payload', 'result'):
            row[key] = json.loads(row[key]) if row[key] else None
    return row

def listing():
    with db() as c:
        return c.execute("SELECT id,created,title,status,stage,progress,error, "
                         "payload::jsonb->>'audience' AS audience, "
                         "result::jsonb->'outcome'->>'verdict' AS verdict "
                         "FROM tests ORDER BY created DESC").fetchall()

def delete(id):
    with db() as c:
        for table in ('checkpoint_writes', 'checkpoint_blobs', 'checkpoints'):
            c.execute(sql.SQL('DELETE FROM {} WHERE thread_id IN (%s,%s)').format(sql.Identifier(table)), (id, 'chat:' + id))
        c.execute('DELETE FROM tests WHERE id=%s', (id,))

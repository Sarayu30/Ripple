import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.getenv('DATA_DIR','./data')).resolve()
ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
MEDIA = ROOT / 'private'
MEDIA.mkdir(exist_ok=True, mode=0o700)

def db():
    connection = sqlite3.connect(ROOT / 'ripple.sqlite3', timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    return connection

def init():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS tests (id TEXT PRIMARY KEY, created TEXT, title TEXT, status TEXT, stage TEXT, progress INTEGER, payload TEXT, result TEXT, error TEXT)')
        c.execute("UPDATE tests SET status='interrupted', error='Server restarted. Retry to reuse completed persona evaluations.' WHERE status IN ('queued','running')")

def create(id, payload):
    with db() as c:
        c.execute('INSERT INTO tests VALUES (?,?,?,?,?,?,?,?,?)', (id,datetime.now(timezone.utc).isoformat(),payload['title'],'queued','Queued',0,json.dumps(payload),None,None))

def update(id, **fields):
    allowed = {'status','stage','progress','result','error'}
    assert fields and set(fields) <= allowed
    if 'result' in fields: fields['result'] = json.dumps(fields['result'])
    with db() as c:
        c.execute('UPDATE tests SET '+','.join(f'{k}=?' for k in fields)+' WHERE id=?', [*fields.values(), id])

def get(id):
    with db() as c: row = c.execute('SELECT * FROM tests WHERE id=?',(id,)).fetchone()
    if not row: return None
    row = dict(row)
    for key in ('payload','result'):
        row[key] = json.loads(row[key]) if row[key] else None
    return row

def listing():
    with db() as c:
        return [dict(r) for r in c.execute('SELECT id,created,title,status,stage,progress,error FROM tests ORDER BY created DESC')]

def delete(id):
    with db() as c: c.execute('DELETE FROM tests WHERE id=?',(id,))

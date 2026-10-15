"""Atomic queue admission, duplicate protection and rolling 24-hour budgets.

Usage is deliberately independent of simulation deletion. These are request /
viewer allowances, not a guarantee of a particular provider dollar cost.
"""
import hashlib
import json
import os
import re
import uuid
from fastapi import HTTPException
from . import auth, store


def setup(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS usage_events ('
        'id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL, units INTEGER NOT NULL, '
        'created TIMESTAMPTZ NOT NULL DEFAULT now())')
    connection.execute('CREATE INDEX IF NOT EXISTS usage_created_idx ON usage_events (created,owner_id,kind)')
    connection.execute('CREATE TABLE IF NOT EXISTS submission_keys ('
        'owner_id TEXT NOT NULL, key TEXT NOT NULL, fingerprint TEXT NOT NULL, '
        'test_id TEXT NOT NULL REFERENCES tests(id) ON DELETE CASCADE, PRIMARY KEY(owner_id,key))')


def lock(connection):
    connection.execute('SELECT pg_advisory_xact_lock(hashtext(current_schema()), 72419706)')


def charge_in(connection, kind, units):
    limits = ('DAILY_VIEWER_BUDGET', 'GLOBAL_DAILY_VIEWER_BUDGET', 500, 2000) if kind == 'viewers' else ('DAILY_CHAT_BUDGET', 'GLOBAL_DAILY_CHAT_BUDGET', 30, 200)
    row = connection.execute("SELECT COALESCE(SUM(units),0) AS total, "
        "COALESCE(SUM(units) FILTER (WHERE owner_id=%s),0) AS own FROM usage_events "
        "WHERE kind=%s AND created > now()-interval '24 hours'", (auth.owner(), kind)).fetchone()
    if row['own'] + units > int(os.getenv(limits[0], str(limits[2]))):
        raise HTTPException(429, 'Your rolling 24-hour usage allowance has been reached. Try again later.')
    if row['total'] + units > int(os.getenv(limits[1], str(limits[3]))):
        raise HTTPException(429, 'The service usage allowance has been reached. Try again later.')
    connection.execute('INSERT INTO usage_events (id,owner_id,kind,units) VALUES (%s,%s,%s,%s)',
                       (str(uuid.uuid4()), auth.owner(), kind, units))


def charge(kind, units):
    with store.db() as connection:
        lock(connection)
        charge_in(connection, kind, units)


def admit(identifier, payload, key=None, media_hash=''):
    if key and not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
        raise HTTPException(422, 'Invalid submission key.')
    fingerprint = hashlib.sha256((json.dumps(payload, sort_keys=True) + media_hash).encode()).hexdigest()
    with store.db() as connection:
        lock(connection)
        if key:
            previous = connection.execute('SELECT test_id,fingerprint FROM submission_keys WHERE owner_id=%s AND key=%s', (auth.owner(), key)).fetchone()
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise HTTPException(409, 'This submission key was already used for different content.')
                return previous['test_id']
        counts = connection.execute("SELECT count(*) AS active, count(*) FILTER (WHERE owner_id=%s) AS own "
                                    "FROM tests WHERE status IN ('queued','running')", (auth.owner(),)).fetchone()
        if counts['active'] >= int(os.getenv('MAX_QUEUED_JOBS', '8')) or counts['own'] >= 2:
            raise HTTPException(429, 'The queue is full. Wait for current simulations to finish.')
        saved = connection.execute('SELECT count(*) AS count FROM tests WHERE owner_id=%s', (auth.owner(),)).fetchone()['count']
        if saved >= int(os.getenv('MAX_WORKSPACE_RUNS', '100')):
            raise HTTPException(429, 'Your workspace storage allowance is full. Delete unused simulations first.')
        charge_in(connection, 'viewers', payload.get('size', 25))
        store.insert(connection, identifier, payload)
        if key:
            connection.execute('INSERT INTO submission_keys VALUES (%s,%s,%s,%s)', (auth.owner(),key,fingerprint,identifier))
    return identifier

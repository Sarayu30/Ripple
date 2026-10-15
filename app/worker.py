"""Durable single-runner queue for a backend with one persistent media volume.

An exclusive PostgreSQL advisory lock prevents overlapping backend deployments
from processing the same files. This is deliberately not a distributed worker.
"""
import asyncio
import logging
import os
import psycopg
from . import auth, store

LOCK_ID = 72419705


def enabled(): return os.getenv('JOB_MODE', 'inline') == 'durable'


def acquire():
    connection = psycopg.connect(store.database_url(), autocommit=True, **store.connection_options())
    try:
        row = connection.execute('SELECT pg_try_advisory_lock(hashtext(current_schema()), %s) AS acquired', (LOCK_ID,)).fetchone()
        if not row['acquired']:
            raise RuntimeError('Another Ripple backend owns this database. Stop it before starting a replacement.')
        return connection
    except Exception:
        connection.close()
        raise


def recover():
    with store.db() as connection:
        connection.execute("UPDATE tests SET status='queued', stage='Resuming saved work', error=NULL WHERE status='running'")


def pending(limit):
    with store.db() as connection:
        return connection.execute("SELECT id,owner_id FROM tests WHERE status='queued' ORDER BY created LIMIT %s", (limit,)).fetchall()


async def run(connection, jobs, start):
    try:
        while True:
            # Losing the exclusive connection stops processing, instead of silently
            # continuing without ownership while another backend takes the lock.
            await asyncio.to_thread(connection.execute, 'SELECT 1')
            capacity = max(0, int(os.getenv('MAX_RUNNING_JOBS', '2')) - len(jobs))
            for row in await asyncio.to_thread(pending, capacity):
                if row['id'] in jobs: continue
                context = auth.identity.set(row['owner_id'])
                try:
                    # Cancellation can occur while the pending query is in flight.
                    current = store.get(row['id'])
                    if current and current['status'] == 'queued': start(row['id'])
                finally: auth.identity.reset(context)
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        raise
    except Exception:
        logging.error('Queue stopped after losing database availability; restart the backend to recover.')
        tasks = list(jobs.values())
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise RuntimeError('Queue unavailable') from None

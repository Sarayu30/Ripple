"""Postgres checkpoints offloaded to threads, also supporting Windows Proactor.

Legacy per-run SQLite checkpoints remain readable for exact-stage recovery.
All new runs use PostgreSQL.
"""
import asyncio
from contextlib import asynccontextmanager
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from . import store

_ready = set()

class ThreadedPostgresSaver(PostgresSaver):
    async def aget_tuple(self, config):
        return await asyncio.to_thread(self.get_tuple, config)

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=''):
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        rows = await asyncio.to_thread(lambda: list(self.list(config, filter=filter, before=before, limit=limit)))
        for row in rows:
            yield row

    async def adelete_thread(self, thread_id):
        await asyncio.to_thread(self.delete_thread, thread_id)

def setup():
    key = (store.database_url(), store.schema())
    if key in _ready:
        return
    with psycopg.connect(key[0], autocommit=True, **store.connection_options()) as conn:
        PostgresSaver(conn).setup()
    _ready.add(key)

@asynccontextmanager
async def saver(directory, kind='workflow'):
    legacy = directory / (kind + '.sqlite')
    if legacy.exists():
        async with AsyncSqliteSaver.from_conn_string(str(legacy)) as checkpoint:
            yield checkpoint
        return
    conn = await asyncio.to_thread(psycopg.connect, store.database_url(), autocommit=True, **store.connection_options())
    try:
        yield ThreadedPostgresSaver(conn)
    finally:
        await asyncio.to_thread(conn.close)

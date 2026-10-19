"""Keep uploaded media only while extracting text observations."""
import logging
import time
from . import auth, store

REUPLOAD_MESSAGE = 'Temporary upload is no longer available. Start a new simulation and upload the video again. Saved results remain available.'


def purge_media(directory):
    if directory.is_symlink() or directory.resolve().parent != store.MEDIA.resolve():
        raise ValueError('Invalid media workspace.')
    if not directory.exists():
        return
    for pattern in ('source.*', 'frame-*.jpg', 'audio.wav'):
        for path in directory.glob(pattern):
            path.unlink(missing_ok=True)


def needs_upload(row):
    from .simulation import cached
    directory = store.MEDIA / row['id']
    return (row['payload'].get('sourceType') == 'upload'
            and cached(directory, 'context.json') is None
            and not any(directory.glob('source.*')))


def sweep():
    """Retry failed cleanup and remove abandoned uploads after one hour."""
    with store.db() as c:
        active = {r['id'] for r in c.execute("SELECT id FROM tests WHERE status IN ('preparing','queued','running')")}
        known = {r['id'] for r in c.execute('SELECT id FROM tests')}
    for directory in store.MEDIA.iterdir():
        if not directory.is_dir() or directory.is_symlink() or directory.name in active:
            continue
        if directory.name not in known and time.time() - directory.stat().st_mtime < 3600:
            continue
        try:
            purge_media(directory)
        except OSError:
            logging.error('Temporary media cleanup will be retried for simulation %s', directory.name)


def migrate_legacy_text():
    """Preserve old replay/chat/version JSON before moving off a persistent disk."""
    from .simulation import cached
    with store.db() as c:
        rows = c.execute('SELECT id,owner_id FROM tests').fetchall()
    for row in rows:
        token = auth.identity.set(row['owner_id'])
        try:
            for path in (store.MEDIA / row['id']).glob('*.json'):
                cached(path.parent, path.name)
        finally:
            auth.identity.reset(token)

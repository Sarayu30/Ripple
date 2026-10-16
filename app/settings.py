"""Deployment settings contain no credentials in errors or public responses."""
import os
from urllib.parse import urlsplit


def production():
    return os.getenv('APP_ENV', 'development') == 'production'


def public_origin():
    value = os.getenv('PUBLIC_ORIGIN', '').rstrip('/')
    if value:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment):
            raise RuntimeError('PUBLIC_ORIGIN must be a plain HTTPS origin.')
    return value


def allowed_hosts():
    hosts = [x.strip() for x in os.getenv('ALLOWED_HOSTS', '').split(',') if x.strip()]
    return hosts or ['localhost', '127.0.0.1', '[::1]', 'testserver']


def validate():
    if os.getenv('VERCEL'):
        raise RuntimeError('Run the persistent backend outside Vercel Functions; deploy the web build to Vercel.')
    if not production():
        return
    if not public_origin():
        raise RuntimeError('Production requires PUBLIC_ORIGIN.')
    if not os.getenv('ALLOWED_HOSTS') or any('*' in host for host in allowed_hosts()):
        raise RuntimeError('Production requires explicit ALLOWED_HOSTS without wildcards.')
    from .auth import accounts, managed, public_config
    if os.getenv('AUTH_MODE', 'local') not in ('local', 'neon'):
        raise RuntimeError('AUTH_MODE must be local or neon.')
    if managed():
        public_config()
    elif not accounts() and len(os.getenv('APP_PASSWORD', '')) < 24:
        raise RuntimeError('Production requires invited accounts or an APP_PASSWORD of at least 24 characters.')
    if os.getenv('PERSISTENT_DATA_CONFIRMED') != '1':
        raise RuntimeError('Mount persistent DATA_DIR storage and set PERSISTENT_DATA_CONFIRMED=1.')
    if not os.path.isabs(os.getenv('DATA_DIR', '')):
        raise RuntimeError('Production DATA_DIR must be an absolute persistent mount path.')
    if os.getenv('JOB_MODE') != 'durable':
        raise RuntimeError('Production requires JOB_MODE=durable for queued recovery.')
    if len(os.getenv('ORIGIN_SECRET', '')) < 32:
        raise RuntimeError('Production requires a server-only ORIGIN_SECRET of at least 32 characters.')


def csp():
    from .auth import managed, public_config
    connect = public_config()['url'] if managed() else ''
    return ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' {connect}; "
            "worker-src 'self' blob:; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")

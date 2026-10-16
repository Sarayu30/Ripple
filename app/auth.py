"""Verified Neon Auth identities, with optional Basic accounts for local use."""
import base64
import hashlib
import json
import os
import re
import secrets
from functools import lru_cache
from contextvars import ContextVar
from collections import OrderedDict
from time import monotonic
from urllib.parse import urlsplit

identity = ContextVar('ripple_identity', default=None)
_verified = OrderedDict()


def owner():
    return identity.get() or os.getenv('DEFAULT_WORKSPACE_OWNER', 'local')


def managed():
    return os.getenv('AUTH_MODE', 'local') == 'neon'


def public_config():
    url = os.getenv('NEON_AUTH_BASE_URL', '').rstrip('/')
    if not re.fullmatch(r'https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.neon\.(?:tech|build)/[A-Za-z0-9_-]+/auth', url):
        raise RuntimeError('NEON_AUTH_BASE_URL must be the HTTPS Auth Base URL from Neon, not a database connection string.')
    return {'mode': 'neon', 'url': url}


@lru_cache(maxsize=2)
def jwks_client(issuer):
    import jwt
    return jwt.PyJWKClient(issuer + '/.well-known/jwks.json', cache_jwk_set=True, lifespan=300, timeout=5)


def verify_session(token):
    import jwt
    import uuid
    if not token or len(token) > 8192: return None
    base = public_config()['url']
    parsed = urlsplit(base)
    issuer = f'{parsed.scheme}://{parsed.netloc}'
    try:
        header = jwt.get_unverified_header(token)
        if header.get('alg') != 'EdDSA': return None
        key = jwks_client(base).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=['EdDSA'], issuer=issuer, audience=issuer,
                            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub']}, leeway=5)
        if (claims.get('role') != 'authenticated' or claims.get('banned', False)
                or claims.get('emailVerified') is not True or claims.get('is_anonymous', False)): return None
        subject = str(uuid.UUID(claims['sub']))
        return subject
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
        return None


def accounts():
    try:
        value = json.loads(os.getenv('RIPPLE_ACCOUNTS_JSON', '{}'))
        if not isinstance(value, dict): raise ValueError()
        for name, encoded in value.items():
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,63}', name): raise ValueError()
            if not isinstance(encoded, str) or not re.fullmatch(r'scrypt\$[0-9a-f]{32}\$[0-9a-f]{64}', encoded):
                raise ValueError()
        return value
    except (ValueError, TypeError):
        raise RuntimeError('RIPPLE_ACCOUNTS_JSON must map valid usernames to scrypt password hashes.') from None


def hash_password(password):
    if len(password) < 16: raise ValueError('Use at least 16 characters.')
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f'scrypt${salt.hex()}${digest.hex()}'


def authenticate(header):
    configured = accounts()
    shared = os.getenv('APP_PASSWORD', '')
    if not configured and not shared: return owner()
    try:
        method, value = header.split(' ', 1)
        if method.lower() != 'basic' or len(value) > 2048: return None
        username, password = base64.b64decode(value, validate=True).decode().split(':', 1)
        if not configured:
            return os.getenv('DEFAULT_WORKSPACE_OWNER', 'local') if secrets.compare_digest(password, shared) else None
        encoded = configured.get(username)
        if not encoded: return None
        # Hash the cache key; never retain the plaintext Basic header/password.
        key = hashlib.sha256((header + encoded).encode()).digest()
        now = monotonic()
        if _verified.get(key, 0) > now: return username
        _, salt, digest = encoded.split('$')
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        if secrets.compare_digest(actual.hex(), digest):
            _verified[key] = now + 30
            if len(_verified) > 256: _verified.popitem(last=False)
            return username
    except (ValueError, UnicodeError):
        pass
    return None

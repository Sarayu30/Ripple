import os
import time
import uuid
import unittest
from unittest.mock import patch, Mock
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from app import auth


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.key = ed25519.Ed25519PrivateKey.generate()
        self.env = patch.dict(os.environ, {'NEON_AUTH_BASE_URL': 'https://fixture.neon.tech/auth/auth'})
        self.env.start()
        self.jwks = patch.object(auth, 'jwks_client', return_value=Mock(
            get_signing_key_from_jwt=Mock(return_value=Mock(key=self.key.public_key()))))
        self.jwks.start()
        self.claims = dict(iss='https://fixture.neon.tech', aud='https://fixture.neon.tech',
            exp=int(time.time())+60, iat=int(time.time()), sub=str(uuid.uuid4()),
            role='authenticated', emailVerified=True, banned=False)

    def tearDown(self):
        self.env.stop()
        self.jwks.stop()

    def encode(self, **updates): return jwt.encode({**self.claims, **updates}, self.key, algorithm='EdDSA')

    def test_accepts_only_signed_real_user_sessions(self):
        self.assertEqual(auth.verify_session(self.encode()), self.claims['sub'])
        for changes in [dict(exp=1), dict(iss='https://attacker.neon.tech'),
                        dict(aud='other'), dict(role='admin'), dict(banned=True),
                        dict(emailVerified=False), dict(emailVerified='true'), dict(is_anonymous=True), dict(sub='local')]:
            self.assertIsNone(auth.verify_session(self.encode(**changes)))
        self.assertIsNone(auth.verify_session(jwt.encode(self.claims, 'not-a-real-secret-key' * 3, algorithm='HS256')))

    def test_config_contains_only_public_auth_url(self):
        self.assertEqual(set(auth.public_config()), {'mode', 'url'})
        for url in ['postgresql://user:private@host/auth', 'https://user:private@fixture.neon.tech/auth/auth',
                    'https://fixture.neon.tech.evil.com/auth/auth', 'https://fixture.neon.tech/auth/auth?secret=private']:
            with patch.dict(os.environ, {'NEON_AUTH_BASE_URL': url}):
                with self.assertRaises(RuntimeError) as caught: auth.public_config()
                self.assertNotIn('private', str(caught.exception))

    def test_jwks_uses_database_scoped_auth_url(self):
        auth.verify_session(self.encode())
        auth.jwks_client.assert_called_with('https://fixture.neon.tech/auth/auth')

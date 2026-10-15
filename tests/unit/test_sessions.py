import os
import time
import uuid
import unittest
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from app import auth


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        public = self.key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        self.env = patch.dict(os.environ, {'SUPABASE_URL': 'https://fixture.supabase.co',
            'SUPABASE_PUBLISHABLE_KEY': 'sb_publishable_' + 'x' * 32, 'SUPABASE_JWT_PUBLIC_KEY': public})
        self.env.start()
        self.claims = dict(iss='https://fixture.supabase.co/auth/v1', aud='authenticated',
            exp=int(time.time())+60, iat=int(time.time()), sub=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()), role='authenticated', is_anonymous=False)

    def tearDown(self): self.env.stop()

    def encode(self, **updates): return jwt.encode({**self.claims, **updates}, self.key, algorithm='ES256')

    def test_accepts_only_signed_real_user_sessions(self):
        self.assertEqual(auth.verify_session(self.encode()), self.claims['sub'])
        for changes in [dict(exp=1), dict(iss='https://attacker.supabase.co/auth/v1'),
                        dict(aud='other'), dict(role='service_role'), dict(is_anonymous=True), dict(sub='local')]:
            self.assertIsNone(auth.verify_session(self.encode(**changes)))
        self.assertIsNone(auth.verify_session(jwt.encode(self.claims, 'not-a-real-secret-key' * 3, algorithm='HS256')))

    def test_never_publishes_secret_key(self):
        with patch.dict(os.environ, {'SUPABASE_PUBLISHABLE_KEY': 'sb_secret_private'}):
            with self.assertRaises(RuntimeError) as caught: auth.public_config()
            self.assertNotIn('sb_secret_private', str(caught.exception))

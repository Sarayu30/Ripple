import base64
import json
import os
import unittest
from unittest.mock import patch
from app import auth


class AuthTests(unittest.TestCase):
    def test_distinct_accounts_and_revocation(self):
        hashed = auth.hash_password('test-password-long-enough')
        header = 'Basic ' + base64.b64encode(b'alice:test-password-long-enough').decode()
        with patch.dict(os.environ, {'RIPPLE_ACCOUNTS_JSON': json.dumps({'alice': hashed}), 'APP_PASSWORD': 'shared'}):
            self.assertEqual(auth.authenticate(header), 'alice')
            self.assertIsNone(auth.authenticate('Basic ' + base64.b64encode(b'bob:shared').decode()))
            with patch.dict(os.environ, {'RIPPLE_ACCOUNTS_JSON': json.dumps({'bob': hashed})}):
                self.assertIsNone(auth.authenticate(header))

    def test_malformed_configuration_never_echoed(self):
        with patch.dict(os.environ, {'RIPPLE_ACCOUNTS_JSON': 'private-value'}):
            with self.assertRaises(RuntimeError) as caught: auth.accounts()
            self.assertNotIn('private-value', str(caught.exception))

    def test_context_is_reset(self):
        token = auth.identity.set('alice')
        self.assertEqual(auth.owner(), 'alice')
        auth.identity.reset(token)
        self.assertNotEqual(auth.owner(), 'alice')

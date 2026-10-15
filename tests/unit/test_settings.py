import os
import unittest
from unittest.mock import patch
from app import settings


class SettingsTests(unittest.TestCase):
    def test_production_fails_closed(self):
        with patch.dict(os.environ, {'APP_ENV': 'production'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'PUBLIC_ORIGIN'):
                settings.validate()

    def test_invalid_origins(self):
        for origin in ['http://example.com', 'https://user:password@example.com', 'https://example.com/path']:
            with patch.dict(os.environ, {'PUBLIC_ORIGIN': origin}, clear=True):
                with self.assertRaises(RuntimeError): settings.public_origin()

    def test_vercel_cannot_start_background_backend(self):
        with patch.dict(os.environ, {'VERCEL': '1'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'persistent backend'): settings.validate()

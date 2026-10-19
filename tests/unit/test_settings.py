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

    def test_production_accepts_temporary_disk_with_protected_accounts(self):
        from pathlib import Path
        values = {'APP_ENV':'production', 'PUBLIC_ORIGIN':'https://ripple.example.com',
                  'ALLOWED_HOSTS':'ripple.example.com', 'AUTH_MODE':'local',
                  'APP_PASSWORD':'x'*32, 'ORIGIN_SECRET':'y'*32,
                  'DATA_DIR':str(Path('artifacts').resolve()), 'JOB_MODE':'durable'}
        with patch.dict(os.environ, values, clear=True):
            settings.validate()

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from email_service import load_env, build_url_email


class TestLoadEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env')
        self.env_path = self.tmp.name

    def tearDown(self):
        os.unlink(self.env_path)

    def _write(self, content):
        self.tmp.write(content)
        self.tmp.close()

    def test_simple_key_value(self):
        self._write('SMTP_HOST=smtp.gmail.com\n')
        # Override PROJECT_ROOT path resolution by patching
        env = self._load_from(self.env_path)
        self.assertEqual(env.get('SMTP_HOST'), 'smtp.gmail.com')

    def test_quoted_value(self):
        self._write('SMTP_PASSWORD="my pass word"\n')
        env = self._load_from(self.env_path)
        self.assertEqual(env.get('SMTP_PASSWORD'), 'my pass word')

    def test_export_prefix(self):
        self._write('export SMTP_USER=user@example.com\n')
        env = self._load_from(self.env_path)
        self.assertEqual(env.get('SMTP_USER'), 'user@example.com')

    def test_comment_line(self):
        self._write('# this is a comment\nSMTP_HOST=mail.example.com\n')
        env = self._load_from(self.env_path)
        self.assertIsNone(env.get('# this is a comment'))
        self.assertEqual(env.get('SMTP_HOST'), 'mail.example.com')

    def _load_from(self, path):
        # Monkey-patch the env_path resolution
        import email_service
        original_root = email_service.PROJECT_ROOT
        try:
            email_service.PROJECT_ROOT = os.path.dirname(path)
            return load_env()
        finally:
            email_service.PROJECT_ROOT = original_root


class TestBuildUrlEmail(unittest.TestCase):
    def test_contains_tunnel_url(self):
        url = 'https://test.trycloudflare.com'
        html = build_url_email(url)
        self.assertIn(url, html)
        self.assertIn('Remote Mouse', html)

    def test_valid_html(self):
        html = build_url_email('https://example.com')
        self.assertTrue(html.strip().startswith('<!DOCTYPE html>'))


if __name__ == '__main__':
    unittest.main()

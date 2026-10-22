import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spotify_lyrics.config import DEFAULT_REDIRECT_URI, load_settings, settings_directory


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write_config(self, content):
        (self.directory / "config.ini").write_text(content, encoding="utf-8")

    def test_missing_credentials_have_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "config.example.ini"):
            load_settings(self.directory, {})

    def test_reads_config_and_default_redirect(self):
        self.write_config("[spotify]\nclient_id = example\nclient_secret = local-secret\n")
        settings = load_settings(self.directory, {})
        self.assertEqual(settings.client_id, "example")
        self.assertEqual(settings.client_secret, "local-secret")
        self.assertEqual(settings.redirect_uri, DEFAULT_REDIRECT_URI)
        self.assertNotIn("local-secret", repr(settings))

    def test_environment_overrides_local_config(self):
        self.write_config("[spotify]\nclient_id = old\nclient_secret = old\n")
        settings = load_settings(
            self.directory,
            {
                "SPOTIPY_CLIENT_ID": "new",
                "SPOTIPY_CLIENT_SECRET": "new-secret",
                "SPOTIPY_REDIRECT_URI": "http://127.0.0.1:9000/callback",
            },
        )
        self.assertEqual(settings.client_id, "new")
        self.assertEqual(settings.client_secret, "new-secret")
        self.assertEqual(settings.redirect_uri, "http://127.0.0.1:9000/callback")

    def test_malformed_config_has_safe_error(self):
        self.write_config("invalid config with secret")
        with self.assertRaisesRegex(ValueError, "Format config.ini tidak valid"):
            load_settings(self.directory, {})

    def test_frozen_application_uses_executable_directory(self):
        with (
            patch("sys.frozen", True, create=True),
            patch(
                "sys.executable",
                str(self.directory / "SpotifyLyrics.exe"),
            ),
        ):
            self.assertEqual(settings_directory(), self.directory.resolve())

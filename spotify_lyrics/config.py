"""Local Spotify settings; imports never trigger authentication."""

import os
import sys
from configparser import ConfigParser
from configparser import Error as ConfigError
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str
    directory: Path


def settings_directory():
    """Read settings beside the executable, or from the source project root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def load_settings(directory=None, environ=None):
    directory = Path(directory) if directory is not None else settings_directory()
    environ = os.environ if environ is None else environ
    parser = ConfigParser(interpolation=None)
    try:
        parser.read(directory / "config.ini", encoding="utf-8")
    except ConfigError as exc:
        raise ValueError("Format config.ini tidak valid. Gunakan config.example.ini.") from exc

    def value(key, env_name, default=""):
        return environ.get(env_name, parser.get("spotify", key, fallback=default)).strip()

    client_id = value("client_id", "SPOTIPY_CLIENT_ID")
    client_secret = value("client_secret", "SPOTIPY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "Konfigurasi Spotify belum lengkap. Salin config.example.ini ke config.ini "
            "dan isi client_id serta client_secret, atau atur SPOTIPY_CLIENT_ID "
            "dan SPOTIPY_CLIENT_SECRET."
        )
    redirect_uri = value("redirect_uri", "SPOTIPY_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    if not redirect_uri:
        raise ValueError("redirect_uri tidak boleh kosong.")
    return Settings(client_id, client_secret, redirect_uri, directory)

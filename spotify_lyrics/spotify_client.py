"""Spotify OAuth client and playback metadata."""

import logging

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)
SCOPE = "user-read-currently-playing user-read-playback-state"


def create_client(settings):
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            redirect_uri=settings.redirect_uri,
            scope=SCOPE,
            cache_path=str(settings.directory / ".spotify_cache"),
        )
    )


def get_current_playback(client):
    try:
        data = client.current_playback(additional_types="track")
        if not data or not data.get("item") or data["item"].get("type") != "track":
            return None
        item = data["item"]
        return {
            "id": item["id"],
            "title": item["name"],
            "artist": ", ".join(a["name"] for a in item["artists"]),
            "album": item["album"]["name"],
            "duration_ms": item["duration_ms"],
            "progress_ms": data["progress_ms"],
            "is_playing": data["is_playing"],
        }
    except Exception as e:
        logger.warning("Spotify error: %s", e)
        return None

"""Poll Spotify off the UI thread and send updates through a queue."""

import logging
import math
import time

from .lyrics import LyricsFetchError, LyricsRateLimited, fetch_lyrics
from .spotify_client import get_current_playback

POLL_INTERVAL = 2.0
logger = logging.getLogger(__name__)


def lyrics_worker(client, updates, stop):
    current_track_id = None
    lyric_mode = None
    pending = False
    retry_at = 0.0
    backoff = 60.0
    retry_message = ""
    fetch_failures = 0

    def send(method, *args):
        updates.put((method, args))

    while not stop.is_set():
        playback = get_current_playback(client)
        if stop.is_set():
            return

        if not playback:
            current_track_id = None
            lyric_mode = None
            pending = False
            send("set_plain_text", "Tidak ada lagu yang diputar")
            stop.wait(POLL_INTERVAL)
            continue

        if playback["id"] != current_track_id:
            current_track_id = playback["id"]
            lyric_mode = None
            pending = True
            fetch_failures = 0

        if pending and time.monotonic() < retry_at:
            remaining = math.ceil(retry_at - time.monotonic())
            send("set_plain_text", f"{retry_message}. Coba lagi dalam {remaining} detik.")
        elif pending:
            send("set_plain_text", "Mencari lirik...")
            try:
                lyrics = fetch_lyrics(
                    playback["title"],
                    playback["artist"],
                    playback["album"],
                    playback["duration_ms"],
                )
            except LyricsFetchError as exc:
                fetch_failures += 1
                delay = 0 if fetch_failures == 1 else POLL_INTERVAL
                retry_message = "Layanan lirik gagal diakses"
                if isinstance(exc, LyricsRateLimited):
                    delay = exc.retry_after if exc.retry_after is not None else backoff
                    retry_message = "LRCLIB membatasi request (429)"
                    backoff = min(backoff * 2, 900)
                retry_at = time.monotonic() + delay
                logger.warning("%s; retry in %.0f seconds", exc, delay)
                send(
                    "set_plain_text",
                    f"{retry_message}. "
                    + (
                        f"Coba lagi dalam {math.ceil(delay)} detik." if delay else "Mencoba lagi..."
                    ),
                )
                if delay:
                    stop.wait(POLL_INTERVAL)
                continue
            pending = False
            fetch_failures = 0
            backoff = 60.0
            retry_at = 0.0
            if stop.is_set():
                return
            if lyrics:
                lyric_mode = lyrics.get("type")
                send("set_lyrics", lyrics)
            else:
                send(
                    "set_plain_text",
                    f"{playback['title']} - {playback['artist']} (lirik tidak ditemukan)",
                )

        if lyric_mode == "synced":
            send(
                "update_progress",
                playback["progress_ms"],
                playback["is_playing"],
                playback["duration_ms"],
                time.monotonic(),
            )
        stop.wait(POLL_INTERVAL)

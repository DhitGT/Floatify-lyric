"""Fetch LRCLIB/Lyrica lyrics and estimate karaoke word timing."""

import logging
import math
import os
import re
import time
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)


class LyricsFetchError(Exception):
    """A service failure, distinct from a track with no lyrics."""


class LyricsRateLimited(LyricsFetchError):
    def __init__(self, retry_after=None):
        super().__init__("LRCLIB rate limited (HTTP 429)")
        self.retry_after = retry_after


def _retry_after(value):
    if not isinstance(value, str):
        return None
    try:
        return max(1, int(value))
    except ValueError:
        try:
            return max(1, parsedate_to_datetime(value).timestamp() - time.time())
        except (TypeError, ValueError, OverflowError):
            return None


def fetch_lyrics(title, artist, album, duration_ms):
    primary_error = None
    try:
        lyrics = _fetch_lrclib(title, artist, album, duration_ms)
        if lyrics:
            return lyrics
    except LyricsFetchError as exc:
        primary_error = exc
        logger.warning("%s; trying Lyrica fallback", exc)

    try:
        lyrics = _fetch_lyrica(title, artist)
    except LyricsFetchError:
        if primary_error is not None:
            raise primary_error
        raise
    if lyrics:
        return lyrics
    if primary_error is not None:
        raise primary_error
    return None


def _fetch_lyrica(title, artist):
    base_url = os.environ.get("LYRICA_BASE_URL", "https://test-0k.onrender.com").rstrip("/")
    try:
        resp = requests.get(
            f"{base_url}/lyrics/",
            params={
                "artist": artist,
                "song": title,
                "timestamps": "true",
                "sequence": "7,3,4,5,6,1",
                "pass": "true",
                "fast": "true",
            },
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise LyricsFetchError(f"Lyrica HTTP {resp.status_code}")
        payload = resp.json()
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise LyricsFetchError("Lyrica returned an invalid or unsuccessful response")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise LyricsFetchError("Lyrica returned invalid lyrics data")

        timed = data.get("timed_lyrics")
        lines = []
        if isinstance(timed, list):
            for entry in timed:
                if not isinstance(entry, dict):
                    continue
                start = entry.get("start_time")
                text = entry.get("text")
                if (
                    isinstance(start, (int, float))
                    and not isinstance(start, bool)
                    and math.isfinite(start)
                    and start >= 0
                    and isinstance(text, str)
                ):
                    lines.append((int(start), text.strip()))
        if lines:
            return {"type": "synced", "lyrics": sorted(lines, key=lambda line: line[0])}
        plain = data.get("lyrics")
        if isinstance(plain, str) and plain.strip():
            return {"type": "plain", "lyrics": plain}
        return None
    except (requests.RequestException, ValueError) as exc:
        raise LyricsFetchError("Lyrica request failed") from exc


def _fetch_lrclib(title, artist, album, duration_ms):
    try:
        resp = requests.get(
            "https://lrclib.net/api/get",
            params={
                "track_name": title,
                "artist_name": artist,
                "album_name": album,
                "duration": round(duration_ms / 1000),
            },
            timeout=5,
        )

        if resp.status_code == 429:
            raise LyricsRateLimited(_retry_after(resp.headers.get("Retry-After")))
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise LyricsFetchError(f"LRCLIB HTTP {resp.status_code}")

        data = resp.json()
        if not isinstance(data, dict):
            raise LyricsFetchError("LRCLIB returned invalid lyrics data")

        synced = data.get("syncedLyrics")
        if synced:
            return {
                "type": "synced",
                "lyrics": parse_lrc(synced),
            }

        plain = data.get("plainLyrics")
        if plain:
            return {
                "type": "plain",
                "lyrics": plain,
            }

        return None

    except LyricsFetchError:
        raise
    except (requests.RequestException, ValueError) as e:
        logger.warning("Lyrics fetch error: %s", e)
        raise LyricsFetchError("LRCLIB request failed") from e


def parse_lrc(lrc_text):
    lines = []
    pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")
    for line in lrc_text.splitlines():
        m = pattern.match(line.strip())
        if m:
            minute, second, text = m.groups()
            ms = int((int(minute) * 60 + float(second)) * 1000)
            text = text.strip()
            lines.append((ms, text))
    lines.sort(key=lambda x: x[0])
    return lines


def build_word_timing(text, start_ms, end_ms):
    words = text.split()
    if not words:
        return [], ""

    total_chars = sum(len(w) for w in words) or 1
    span = max(end_ms - start_ms, 1)

    timing = []
    cursor_ms = float(start_ms)
    char_offset = 0
    for w in words:
        dur = span * (len(w) / total_chars)
        w_start = cursor_ms
        w_end = cursor_ms + dur

        idx_start = f"1.{char_offset}"
        char_offset += len(w)
        idx_end = f"1.{char_offset}"
        char_offset += 1

        timing.append(
            {
                "start_ms": w_start,
                "end_ms": w_end,
                "idx_start": idx_start,
                "idx_end": idx_end,
            }
        )
        cursor_ms = w_end

    display_text = " ".join(words)
    return timing, display_text

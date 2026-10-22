import unittest
from unittest.mock import Mock, patch

import requests

from spotify_lyrics.lyrics import (
    LyricsFetchError,
    LyricsRateLimited,
    build_word_timing,
    fetch_lyrics,
    parse_lrc,
)


class LyricsTests(unittest.TestCase):
    def test_parse_lrc_sorts_timestamps_and_ignores_metadata(self):
        self.assertEqual(
            parse_lrc("[ar:Someone]\n[00:12.50] Second \ninvalid\n[00:01.05]First"),
            [(1050, "First"), (12500, "Second")],
        )

    def test_empty_lyric_line_is_preserved(self):
        self.assertEqual(parse_lrc("[01:00.00]"), [(60000, "")])

    def test_word_timing_covers_line_and_matches_text_indices(self):
        timing, text = build_word_timing("  hi   there  ", 1000, 1700)
        self.assertEqual(text, "hi there")
        self.assertEqual(timing[0]["start_ms"], 1000)
        self.assertAlmostEqual(timing[0]["end_ms"], 1200)
        self.assertAlmostEqual(timing[1]["end_ms"], 1700)
        self.assertEqual(timing[1]["idx_start"], "1.3")
        self.assertEqual(timing[1]["idx_end"], "1.8")

    def test_empty_text_has_no_words(self):
        self.assertEqual(build_word_timing("   ", 0, 1000), ([], ""))

    def test_zero_duration_still_produces_positive_word_duration(self):
        timing, _ = build_word_timing("hello", 1000, 1000)
        self.assertGreater(timing[0]["end_ms"], timing[0]["start_ms"])

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_synced_lyrics_take_priority(self, get):
        get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"syncedLyrics": "[00:01.00]Hello", "plainLyrics": "Hello"}),
        )
        self.assertEqual(
            fetch_lyrics("Song", "Artist", "Album", 150000),
            {
                "type": "synced",
                "lyrics": [(1000, "Hello")],
            },
        )
        self.assertEqual(get.call_args.kwargs["params"]["duration"], 150)
        self.assertEqual(get.call_args.kwargs["timeout"], 5)

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_plain_lyrics_fallback(self, get):
        get.return_value = Mock(status_code=200, json=Mock(return_value={"plainLyrics": "Hello"}))
        self.assertEqual(
            fetch_lyrics("Song", "Artist", "Album", 1000),
            {
                "type": "plain",
                "lyrics": "Hello",
            },
        )

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_missing_lyrics_return_none(self, get):
        get.return_value = Mock(status_code=404)
        self.assertIsNone(fetch_lyrics("Song", "Artist", "Album", 1000))

    @patch("spotify_lyrics.lyrics._fetch_lyrica", return_value=None)
    @patch("spotify_lyrics.lyrics.requests.get")
    def test_rate_limit_preserves_retry_after(self, get, _fallback):
        for header, expected in [("120", 120), (None, None), ("invalid", None)]:
            with self.subTest(header=header):
                get.return_value = Mock(status_code=429, headers={"Retry-After": header})
                with self.assertRaises(LyricsRateLimited) as error:
                    fetch_lyrics("Song", "Artist", "Album", 1000)
                self.assertEqual(error.exception.retry_after, expected)

    @patch("spotify_lyrics.lyrics._fetch_lyrica", return_value=None)
    @patch("spotify_lyrics.lyrics.time.time", return_value=0)
    @patch("spotify_lyrics.lyrics.requests.get")
    def test_rate_limit_accepts_http_date(self, get, _clock, _fallback):
        get.return_value = Mock(
            status_code=429, headers={"Retry-After": "Thu, 01 Jan 1970 00:02:00 GMT"}
        )
        with self.assertRaises(LyricsRateLimited) as error:
            fetch_lyrics("Song", "Artist", "Album", 1000)
        self.assertEqual(error.exception.retry_after, 120)

    @patch("spotify_lyrics.lyrics._fetch_lyrica", return_value=None)
    @patch("spotify_lyrics.lyrics.requests.get")
    def test_service_and_network_failures_are_not_missing_lyrics(self, get, _fallback):
        get.return_value = Mock(status_code=503)
        with self.assertRaises(LyricsFetchError):
            fetch_lyrics("Song", "Artist", "Album", 1000)
        get.side_effect = requests.Timeout("timeout")
        with self.assertRaises(LyricsFetchError):
            fetch_lyrics("Song", "Artist", "Album", 1000)


class LyricsFallbackTests(unittest.TestCase):
    @patch("spotify_lyrics.lyrics.requests.get")
    def test_lrclib_success_does_not_call_fallback(self, get):
        get.return_value = Mock(status_code=200, json=Mock(return_value={"plainLyrics": "Hi"}))
        self.assertEqual(fetch_lyrics("Song", "Artist", "Album", 1000)["lyrics"], "Hi")
        get.assert_called_once()

    @patch.dict("os.environ", {"LYRICA_BASE_URL": "http://localhost:9999/"})
    @patch("spotify_lyrics.lyrics.requests.get")
    def test_fallback_converts_millisecond_timestamps_and_skips_lrclib_source(self, get):
        for first in (
            Mock(status_code=503),
            Mock(status_code=429, headers={"Retry-After": "120"}),
            Mock(status_code=404),
            Mock(status_code=200, json=Mock(return_value={})),
            Mock(status_code=200, json=Mock(side_effect=ValueError("bad JSON"))),
            Mock(status_code=200, json=Mock(return_value=[])),
            requests.Timeout("timeout"),
        ):
            with self.subTest(first=first):
                get.side_effect = [
                    first,
                    Mock(
                        status_code=200,
                        json=Mock(
                            return_value={
                                "status": "success",
                                "data": {
                                    "lyrics": "Hello\nWorld",
                                    "timed_lyrics": [
                                        {"start_time": 2000, "text": " World "},
                                        {"start_time": 0, "text": "Hello"},
                                    ],
                                },
                            }
                        ),
                    ),
                ]
                self.assertEqual(
                    fetch_lyrics("Song", "Artist", "Album", 1000),
                    {"type": "synced", "lyrics": [(0, "Hello"), (2000, "World")]},
                )
                self.assertEqual(get.call_args.args[0], "http://localhost:9999/lyrics/")
                params = get.call_args.kwargs["params"]
                self.assertEqual(params["song"], "Song")
                self.assertEqual(params["artist"], "Artist")
                self.assertNotIn("2", params["sequence"].split(","))
                self.assertEqual(params["pass"], "true")

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_fallback_plain_lyrics_when_timestamps_are_invalid(self, get):
        get.side_effect = [
            Mock(status_code=404),
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "status": "success",
                        "data": {
                            "lyrics": "Hello",
                            "timed_lyrics": [
                                {"start_time": "invalid", "text": "Hi"},
                                {"start_time": float("nan"), "text": "Hi"},
                                {"start_time": -1, "text": "Hi"},
                                None,
                            ],
                        },
                    }
                ),
            ),
        ]
        self.assertEqual(
            fetch_lyrics("Song", "Artist", "Album", 1000),
            {"type": "plain", "lyrics": "Hello"},
        )

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_both_missing_return_none(self, get):
        get.side_effect = [Mock(status_code=404), Mock(status_code=404)]
        self.assertIsNone(fetch_lyrics("Song", "Artist", "Album", 1000))

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_fallback_failure_keeps_primary_rate_limit(self, get):
        get.side_effect = [
            Mock(status_code=429, headers={"Retry-After": "120"}),
            requests.Timeout("timeout"),
        ]
        with self.assertRaises(LyricsRateLimited) as error:
            fetch_lyrics("Song", "Artist", "Album", 1000)
        self.assertEqual(error.exception.retry_after, 120)

    @patch("spotify_lyrics.lyrics.requests.get")
    def test_fallback_errors_are_retryable_when_primary_has_no_lyrics(self, get):
        for fallback in (
            Mock(status_code=503),
            Mock(status_code=200, json=Mock(side_effect=ValueError("bad JSON"))),
            Mock(status_code=200, json=Mock(return_value=[])),
            Mock(status_code=200, json=Mock(return_value={"status": "error"})),
            Mock(status_code=200, json=Mock(return_value={"status": "success", "data": []})),
            requests.Timeout("timeout"),
        ):
            with self.subTest(fallback=fallback):
                get.side_effect = [Mock(status_code=404), fallback]
                with self.assertRaises(LyricsFetchError):
                    fetch_lyrics("Song", "Artist", "Album", 1000)

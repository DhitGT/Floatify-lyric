import threading
import unittest
from queue import Queue
from unittest.mock import Mock, patch

from spotify_lyrics.lyrics import LyricsFetchError, LyricsRateLimited
from spotify_lyrics.spotify_client import get_current_playback
from spotify_lyrics.worker import lyrics_worker


class PlaybackTests(unittest.TestCase):
    def test_no_playback_returns_none(self):
        self.assertIsNone(get_current_playback(Mock(current_playback=Mock(return_value=None))))

    def test_episode_is_ignored(self):
        client = Mock(current_playback=Mock(return_value={"item": {"type": "episode"}}))
        self.assertIsNone(get_current_playback(client))

    def test_track_metadata_is_normalized(self):
        client = Mock(
            current_playback=Mock(
                return_value={
                    "item": {
                        "id": "track",
                        "type": "track",
                        "name": "Song",
                        "artists": [{"name": "One"}, {"name": "Two"}],
                        "album": {"name": "Album"},
                        "duration_ms": 60000,
                    },
                    "progress_ms": 1000,
                    "is_playing": True,
                }
            )
        )
        playback = get_current_playback(client)
        self.assertEqual(playback["artist"], "One, Two")
        self.assertEqual(playback["progress_ms"], 1000)

    @patch("spotify_lyrics.worker.fetch_lyrics")
    @patch("spotify_lyrics.worker.get_current_playback")
    def test_worker_fetches_once_per_track_and_queues_updates(self, playback, fetch):
        track = {
            "id": "track",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "duration_ms": 60000,
            "progress_ms": 1000,
            "is_playing": True,
        }
        playback.return_value = track
        fetch.return_value = {"type": "synced", "lyrics": [(1000, "Hello")]}
        updates = Queue()
        stop = Mock()
        stop.is_set.return_value = False

        def end_after_second_poll(_):
            if playback.call_count == 2:
                stop.is_set.return_value = True

        stop.wait.side_effect = end_after_second_poll
        lyrics_worker(Mock(), updates, stop)
        fetch.assert_called_once()
        methods = []
        while not updates.empty():
            methods.append(updates.get_nowait()[0])
        self.assertEqual(
            methods, ["set_plain_text", "set_lyrics", "update_progress", "update_progress"]
        )

    @patch("spotify_lyrics.worker.get_current_playback")
    def test_worker_does_no_work_after_stop(self, playback):
        stop = threading.Event()
        stop.set()
        lyrics_worker(Mock(), Queue(), stop)
        playback.assert_not_called()

    @patch("spotify_lyrics.worker.time.monotonic")
    @patch("spotify_lyrics.worker.fetch_lyrics")
    @patch("spotify_lyrics.worker.get_current_playback")
    def test_fetch_failure_retries_immediately_then_at_poll_interval(self, playback, fetch, clock):
        playback.return_value = {
            "id": "track",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "duration_ms": 60000,
        }
        for failures in (1, 2):
            with self.subTest(failures=failures):
                fetch.reset_mock()
                fetch.side_effect = [LyricsFetchError("unavailable")] * failures + [
                    {"type": "plain", "lyrics": "Hello"}
                ]
                clock.return_value = 0
                stop = Mock()
                stop.is_set.return_value = False
                calls_before_wait = []

                def advance(delay):
                    calls_before_wait.append(fetch.call_count)
                    clock.return_value += delay
                    if fetch.call_count == failures + 1:
                        stop.is_set.return_value = True

                stop.wait.side_effect = advance
                updates = Queue()
                lyrics_worker(Mock(), updates, stop)
                self.assertEqual(calls_before_wait, list(range(2, failures + 2)))
                self.assertIn(
                    ("set_lyrics", ({"type": "plain", "lyrics": "Hello"},)),
                    list(updates.queue),
                )

    @patch("spotify_lyrics.worker.time.monotonic")
    @patch("spotify_lyrics.worker.fetch_lyrics")
    @patch("spotify_lyrics.worker.get_current_playback")
    def test_rate_limit_waits_across_track_changes_then_retries_current_track(
        self, playback, fetch, clock
    ):
        track = {
            "id": "first",
            "title": "First",
            "artist": "Artist",
            "album": "Album",
            "duration_ms": 60000,
            "progress_ms": 1000,
            "is_playing": True,
        }
        playback.side_effect = [
            track,
            dict(track, id="second", title="Second"),
            dict(track, id="second", title="Second"),
        ]
        fetch.side_effect = [LyricsRateLimited(60), {"type": "plain", "lyrics": "Hello"}]
        clock.return_value = 0
        stop = Mock()
        stop.is_set.return_value = False
        calls = []

        def advance(_):
            calls.append(fetch.call_count)
            clock.return_value += 30
            if len(calls) == 3:
                stop.is_set.return_value = True

        stop.wait.side_effect = advance
        updates = Queue()
        lyrics_worker(Mock(), updates, stop)
        self.assertEqual(calls, [1, 1, 2])
        self.assertEqual(fetch.call_args.args[0], "Second")
        messages = list(updates.queue)
        self.assertFalse(any("tidak ditemukan" in str(message) for message in messages))
        self.assertIn(("set_lyrics", ({"type": "plain", "lyrics": "Hello"},)), messages)

    @patch("spotify_lyrics.worker.time.monotonic")
    @patch("spotify_lyrics.worker.fetch_lyrics")
    @patch("spotify_lyrics.worker.get_current_playback")
    def test_repeated_rate_limits_back_off_without_retry_after(self, playback, fetch, clock):
        playback.return_value = {
            "id": "track",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "duration_ms": 60000,
        }
        fetch.side_effect = LyricsRateLimited()
        clock.return_value = 0
        stop = Mock()
        stop.is_set.return_value = False
        calls = []

        def advance(_):
            calls.append(fetch.call_count)
            clock.return_value += 60
            if len(calls) == 4:
                stop.is_set.return_value = True

        stop.wait.side_effect = advance
        lyrics_worker(Mock(), Queue(), stop)
        self.assertEqual(calls, [1, 2, 2, 3])

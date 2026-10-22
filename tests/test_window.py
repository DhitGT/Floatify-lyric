import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from spotify_lyrics.window import FloatingLyrics


class WindowInteractionTests(unittest.TestCase):
    def setUp(self):
        # Exercise event handling without creating a desktop window.
        self.window = FloatingLyrics.__new__(FloatingLyrics)
        self.window.root = Mock()
        self.window.root.winfo_width.return_value = 720
        self.window.root.winfo_height.return_value = 80
        self.window.root.winfo_x.return_value = 100
        self.window.root.winfo_y.return_value = 200

    def test_center_drag_moves_without_resizing(self):
        self.window.on_press(SimpleNamespace(x=360, y=40, x_root=460, y_root=240))
        self.window.on_drag(SimpleNamespace(x_root=500, y_root=270))
        self.window.root.geometry.assert_called_once_with("+140+230")

    def test_corner_drag_resizes_from_original_geometry(self):
        self.window.on_press(SimpleNamespace(x=720, y=80, x_root=820, y_root=280))
        self.window.on_drag(SimpleNamespace(x_root=920, y_root=330))
        self.window.root.geometry.assert_called_once_with("820x130+100+200")

    def test_resize_respects_minimum_size(self):
        self.window.on_press(SimpleNamespace(x=0, y=0, x_root=100, y_root=200))
        self.window.on_drag(SimpleNamespace(x_root=2000, y_root=2000))
        self.window.root.geometry.assert_called_once_with("30x18+790+262")

    def test_status_text_clears_old_karaoke_state(self):
        self.window.text = Mock()
        self.window._progress_state = (1000, True, 60000, 0)
        self.window.lines = [(1000, "old song")]
        self.window.current_words = ["old"]
        self.window.set_plain_text("status")
        self.assertIsNone(self.window._progress_state)
        self.assertIsNone(self.window.lines)
        self.assertEqual(self.window.current_words, [])

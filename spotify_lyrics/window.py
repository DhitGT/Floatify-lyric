"""Tkinter overlay: dragging, resizing, and karaoke highlighting."""

import bisect
import time
import tkinter as tk
import tkinter.font as tkfont

from .lyrics import build_word_timing

MIN_W, MIN_H = 30, 18
BORDER = 8
TOPMOST_INTERVAL_MS = 500
LAST_LINE_DURATION_MS = 6000
COLOR_BACKGROUND = "#1c1c1e"
COLOR_SUNG = "#ffffff"
COLOR_CURRENT = "#1DB954"
COLOR_UPCOMING = "#8e8e93"
COLOR_PLAIN = "#ffffff"


class FloatingLyrics:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        bg_color = COLOR_BACKGROUND
        self.root.configure(bg=bg_color)
        win_w, win_h = (720, 80)
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - win_w) // 2
        y = self.root.winfo_screenheight() - 160
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.font_size = 18
        self.text = tk.Text(
            self.root,
            bg=bg_color,
            fg=COLOR_PLAIN,
            bd=0,
            highlightthickness=0,
            wrap="word",
            cursor="arrow",
            takefocus=0,
            insertwidth=0,
            padx=0,
            pady=0,
            spacing1=0,
            spacing2=0,
            spacing3=0,
            font=("Segoe UI", self.font_size, "bold"),
        )
        self.text.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.text.bindtags((str(self.text), "all"))
        self.text.tag_configure("center", justify="center")
        self.text.tag_configure("sung", foreground=COLOR_SUNG)
        self.text.tag_configure("current", foreground=COLOR_CURRENT)
        self.text.tag_configure("upcoming", foreground=COLOR_UPCOMING)
        self.lines = None
        self.line_starts = []
        self.current_words = []
        self._last_render_key = None
        self._progress_state = None
        self.set_plain_text("Menunggu lagu diputar...")
        self.root.after(50, self._refresh_progress)
        self._resize_edge = None
        for widget in (self.root, self.text):
            widget.bind("<Motion>", self.on_motion)
            widget.bind("<ButtonPress-1>", self.on_press)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.on_release)
            widget.bind("<Button-3>", lambda e: self.root.destroy())
        self.root.bind("<Configure>", self.on_configure)
        self.keep_on_top()

    def _detect_edge(self, x, y, w, h):
        left = x <= BORDER
        right = x >= w - BORDER
        top = y <= BORDER
        bottom = y >= h - BORDER
        if top and left:
            return "nw"
        if top and right:
            return "ne"
        if bottom and left:
            return "sw"
        if bottom and right:
            return "se"
        if left:
            return "w"
        if right:
            return "e"
        if top:
            return "n"
        if bottom:
            return "s"
        return None

    def on_motion(self, event):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        edge = self._detect_edge(event.x, event.y, w, h)
        cursors = {
            "n": "sb_v_double_arrow",
            "s": "sb_v_double_arrow",
            "w": "sb_h_double_arrow",
            "e": "sb_h_double_arrow",
            "nw": "size_nw_se",
            "se": "size_nw_se",
            "ne": "size_ne_sw",
            "sw": "size_ne_sw",
        }
        cursor = cursors.get(edge, "arrow")
        self.root.config(cursor=cursor)
        self.text.config(cursor=cursor)

    def on_press(self, event):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self._resize_edge = self._detect_edge(event.x, event.y, w, h)
        self._start = {
            "x_root": event.x_root,
            "y_root": event.y_root,
            "x": self.root.winfo_x(),
            "y": self.root.winfo_y(),
            "w": w,
            "h": h,
        }

    def on_drag(self, event):
        dx = event.x_root - self._start["x_root"]
        dy = event.y_root - self._start["y_root"]
        x, y = (self._start["x"], self._start["y"])
        w, h = (self._start["w"], self._start["h"])
        edge = self._resize_edge
        if not edge:
            self.root.geometry(f"{x + dx:+d}{y + dy:+d}")
            return
        new_x, new_y, new_w, new_h = (x, y, w, h)
        if "e" in edge:
            new_w = max(MIN_W, w + dx)
        if "s" in edge:
            new_h = max(MIN_H, h + dy)
        if "w" in edge:
            new_w = max(MIN_W, w - dx)
            new_x = x + (w - new_w)
        if "n" in edge:
            new_h = max(MIN_H, h - dy)
            new_y = y + (h - new_h)
        self.root.geometry(f"{int(new_w)}x{int(new_h)}{int(new_x):+d}{int(new_y):+d}")

    def on_release(self, event):
        self._resize_edge = None

    def on_configure(self, event):
        h = self.root.winfo_height()
        w = self.root.winfo_width()
        size = max(6, min(int(h * 0.32), int(w * 0.055)))
        if size != self.font_size:
            self.font_size = size
            f_normal = ("Segoe UI Semibold", size, "bold")
            self.text.config(font=f_normal)
            self.text.tag_configure("sung", font=f_normal)
            self.text.tag_configure("current", font=f_normal)
            self.text.tag_configure("upcoming", font=f_normal)
        line_height = tkfont.Font(font=self.text.cget("font")).metrics("linespace")
        vertical_padding = max(0, (h - line_height) // 2)
        self.text.tag_configure("center", spacing1=vertical_padding)

    def keep_on_top(self):
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.after(TOPMOST_INTERVAL_MS, self.keep_on_top)

    def set_plain_text(self, text):
        self._progress_state = None
        self.lines = None
        self.line_starts = []
        self.current_words = []
        self._last_render_key = None
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text, ("center",))
        self.text.tag_add("center", "1.0", "end")
        self.text.config(state="disabled", fg=COLOR_PLAIN)

    def set_lyrics(self, lyric_data):
        """Tampilkan lirik hasil LRCLIB.

        lyric_data berbentuk:
            {"type": "synced", "lyrics": [(ms, text), ...]}
        atau
            {"type": "plain", "lyrics": "teks lirik..."}
        """
        if not lyric_data:
            self.set_plain_text("Lirik tidak ditemukan")
            return
        lyric_type = lyric_data.get("type")
        lyrics = lyric_data.get("lyrics")
        if lyric_type == "synced":
            safe_lines = []
            for item in lyrics or []:
                try:
                    start_ms, text = item
                    safe_lines.append((int(start_ms), str(text)))
                except (TypeError, ValueError):
                    continue
            safe_lines.sort(key=lambda x: x[0])
            if not safe_lines:
                self.set_plain_text("Lirik sinkron tidak valid")
                return
            self.lines = safe_lines
            self.line_starts = [start_ms for start_ms, _ in safe_lines]
            self.current_words = []
            self._last_render_key = None
            self._progress_state = None
            return
        if lyric_type == "plain":
            self.set_plain_text(str(lyrics or ""))
            return
        self.set_plain_text("Format lirik tidak dikenali")

    def _refresh_progress(self):
        if self._progress_state:
            progress_ms, is_playing, duration_ms, updated_at = self._progress_state
            self.update_progress(progress_ms, is_playing, duration_ms, updated_at)
        self.root.after(50, self._refresh_progress)

    def update_progress(self, progress_ms, is_playing, duration_ms, updated_at=None):
        try:
            progress_ms = int(progress_ms or 0)
            duration_ms = int(duration_ms or 0)
        except (TypeError, ValueError):
            return
        self._progress_state = (
            progress_ms,
            bool(is_playing),
            duration_ms,
            updated_at if updated_at is not None else time.monotonic(),
        )
        if not self.lines or not self.line_starts:
            return
        if is_playing:
            progress_ms += int((time.monotonic() - self._progress_state[3]) * 1000)
        idx = bisect.bisect_right(self.line_starts, progress_ms) - 1
        idx = max(0, min(idx, len(self.lines) - 1))
        render_key = (idx, is_playing)
        if render_key != self._last_render_key:
            self._last_render_key = render_key
            start_ms = self.line_starts[idx]
            end_ms = (
                self.line_starts[idx + 1]
                if idx + 1 < len(self.line_starts)
                else min(start_ms + LAST_LINE_DURATION_MS, duration_ms)
            )
            text = self.lines[idx][1]
            if not text:
                self.current_words = []
                self.text.config(state="normal")
                self.text.delete("1.0", "end")
                self.text.insert("1.0", "♪", ("center", "upcoming"))
                self.text.config(state="disabled")
                return
            timing, display_text = build_word_timing(text, start_ms, end_ms)
            self.current_words = timing
            self.text.config(state="normal")
            self.text.delete("1.0", "end")
            self.text.insert("1.0", display_text)
            if not is_playing:
                self.text.insert("end", "  ⏸")
            self.text.tag_add("center", "1.0", "end")
            self.text.tag_add("upcoming", "1.0", "end")
            self.text.config(state="disabled")
        if not self.current_words:
            return
        for w in self.current_words:
            if progress_ms >= w["end_ms"]:
                tag = "sung"
            elif progress_ms >= w["start_ms"]:
                tag = "current"
            else:
                tag = "upcoming"
            for t in ("sung", "current", "upcoming"):
                self.text.tag_remove(t, w["idx_start"], w["idx_end"])
            self.text.tag_add(tag, w["idx_start"], w["idx_end"])

    def run_forever(self):
        self.root.mainloop()

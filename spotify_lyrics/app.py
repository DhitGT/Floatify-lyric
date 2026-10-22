"""Application entry point and coordination between UI and worker."""

import logging
import sys
import threading
from queue import Empty, Queue

from .config import load_settings, settings_directory
from .spotify_client import create_client
from .window import FloatingLyrics
from .worker import lyrics_worker


def main():
    frozen = getattr(sys, "frozen", False)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        **(
            {"filename": settings_directory() / "spotify_lyrics.log", "encoding": "utf-8"}
            if frozen
            else {}
        ),
    )
    try:
        settings = load_settings()
    except (ValueError, OSError) as exc:
        logging.error("%s", exc)
        if frozen:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Spotify Floating Lyrics", str(exc), parent=root)
            root.destroy()
        return 1

    client = create_client(settings)
    window = FloatingLyrics()
    updates = Queue()
    stop = threading.Event()

    def drain_updates():
        while True:
            try:
                method, args = updates.get_nowait()
            except Empty:
                break
            getattr(window, method)(*args)
        window.root.after(50, drain_updates)

    window.root.after(50, drain_updates)
    threading.Thread(
        target=lyrics_worker,
        args=(client, updates, stop),
        daemon=True,
        name="spotify-lyrics-worker",
    ).start()
    try:
        window.run_forever()
    finally:
        stop.set()
    return 0

"""Compatibility launcher; prefer `python -m spotify_lyrics`."""

from spotify_lyrics.app import main

if __name__ == "__main__":
    raise SystemExit(main())

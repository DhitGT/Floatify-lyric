# Spotify Floating Lyrics

Language: [Indonesia](README.md) | **English**

A lyrics overlay for the song currently playing on Spotify. Built with Python and Tkinter, with a dark panel that you can move and resize.

## Preview

![Animated floating lyrics preview with karaoke highlighting](docs/images/floating-lyrics-preview.gif)

An animated application preview using sample text. Highlighting moves word by word: sung words appear in white, the active word in green, and upcoming words in gray. The panel floats above other applications and can be moved or resized.

[View the static screenshot](docs/images/floating-lyrics-preview.png).

## Features

- Line-synced lyrics from [LRCLIB](https://lrclib.net/).
- Automatic fallback to [Lyrica](https://github.com/thinkely/Lyrica) when LRCLIB fails, rate limits requests, or cannot find lyrics. Lyrica searches sources other than LRCLIB and preserves line timestamps when available.
- Karaoke word highlighting, with timing **estimated** from word length. The overlay uses line timestamps to estimate word timing.
- Plain lyrics when synced lyrics are unavailable.
- Always-on-top window, drag to move, and resize from the edges or corners.
- Font size adjusts to the window size.

## Requirements

- Python 3.11 or newer with Tkinter. Run `python -m tkinter` to check Tkinter.
- An internet connection, a Spotify account, and an application in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
- Development Mode application owners need Spotify Premium. Other accounts must meet Spotify's access requirements. See the [Development Mode requirements](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

This project targets Windows desktops. Acrylic effects and Win32 code have been removed; other desktop platforms have not been verified.

## Run from source

After cloning or downloading the repository, open a terminal in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.ini config.ini
```

In the Spotify Developer Dashboard, register this redirect URI **exactly**:

```text
http://127.0.0.1:8765/callback
```

Spotify allows HTTP for explicit loopback addresses such as `127.0.0.1`; see the [redirect URI guide](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).

Enter your application's `client_id` and `client_secret` in `config.ini`. Do not edit credentials in the Python source. Then run:

```powershell
.\.venv\Scripts\python.exe -m spotify_lyrics
```

When Spotify access is first needed, a browser opens so you can log in and grant permission to read playback. Play a song in Spotify and lyrics will be fetched automatically. You can also use `python index.py` as the launcher.

On macOS/Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`. Some Linux distributions require an additional Tkinter package from the system package manager.

### Configuration and local data

When running from source, `config.ini` is read from the project root, regardless of the terminal's working directory. The following environment variables override the corresponding configuration values or select the Lyrica server:

| Environment variable | Value |
| --- | --- |
| `SPOTIPY_CLIENT_ID` | Spotify client ID |
| `SPOTIPY_CLIENT_SECRET` | Spotify client secret |
| `SPOTIPY_REDIRECT_URI` | Redirect URI; defaults to `http://127.0.0.1:8765/callback` |
| `LYRICA_BASE_URL` | Lyrica server URL; defaults to `https://test-0k.onrender.com`. You can use your own server, such as `http://127.0.0.1:9999` |

The Lyrica fallback uses the public instance listed in the [Lyrica documentation](https://github.com/thinkely/Lyrica/blob/main/guide/USER_GUIDE.md). Instance and lyrics source availability may change. Request timeouts are 5 seconds for LRCLIB and 10 seconds for Lyrica.

Login tokens are stored in `.spotify_cache` in the same directory as the configuration. `config.ini`, tokens, the virtual environment, and build outputs are excluded by `.gitignore`. Do not include these files in issues, pull requests, or shared ZIP archives.

## Controls

| Action | Control |
| --- | --- |
| Move the overlay | Left-click and drag the center |
| Resize | Drag an edge or corner |
| Close the application | Right-click the overlay |

## Build a Windows `.exe`

```powershell
.\build_exe.bat
```

The build output is `dist/SpotifyLyrics.exe`. Copy `config.example.ini` to `config.ini` **beside the executable**, then enter your credentials. Configuration and tokens are not bundled into the executable. This directory must be writable so the application can save tokens and `spotify_lyrics.log`.

The build script installs development dependencies, including PyInstaller. Running the application only requires the dependencies in `requirements.txt`.

## Project structure

```text
spotify_lyrics/
  __main__.py         # python -m spotify_lyrics
  app.py              # startup, UI queue, and worker lifecycle
  config.py           # local/environment configuration
  spotify_client.py   # OAuth and Spotify playback metadata
  lyrics.py           # LRCLIB/Lyrica, LRC parsing, and word timing
  window.py           # Tkinter interface and overlay interactions
  worker.py           # Spotify polling and queued updates
tests/                # tests without Spotify login or network access
.github/              # CI and contribution templates
index.py              # compatibility launcher and build entry point
config.example.ini    # configuration template without credentials
requirements.txt      # runtime dependencies
requirements-dev.txt  # development/build dependencies
build_exe.bat         # Windows executable build
```

## Troubleshooting

- **Incomplete configuration:** copy the template and fill in both credentials. For the `.exe`, place `config.ini` beside the executable.
- **`Cannot find a usable init.tcl`:** the Python Tcl/Tk installation is incomplete. Repair or reinstall Python with Tcl/Tk support, then recreate the virtual environment. The build script checks Tkinter before creating the executable.
- **Redirect URI error:** use the same address and port in the configuration and Dashboard. This project's default port is `8765`.
- **Spotify access denied:** check credentials, the application owner's Premium subscription, and user access in the Dashboard. API errors appear in the terminal or executable log.
- **Nothing is playing:** the application only reads song playback; podcasts and episodes are ignored.
- **Lyrics not found:** neither LRCLIB nor Lyrica found lyrics matching the song metadata.
- **Lyrics service failure:** Lyrica is tried immediately after LRCLIB fails. If both services fail, the application retries immediately once, then every 2 seconds for ordinary failures.
- **LRCLIB rate limit (429):** Lyrica is tried first. If the fallback returns no lyrics, the application waits according to the `Retry-After` header. Without that header, the delay starts at 60 seconds and increases up to 15 minutes on repeated rate limits. Retries use the currently playing song; changing tracks does not bypass the delay.
- **Inaccurate highlighting:** word timing is estimated. Plain lyrics do not have synced highlighting.
- **Log in again or switch accounts:** close the application, delete the local `.spotify_cache` file, then restart.

For contribution instructions and code checks, see [CONTRIBUTING.md](CONTRIBUTING.md) (Indonesian).

This project is not affiliated with Spotify or LRCLIB.

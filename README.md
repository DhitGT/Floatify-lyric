# Spotify Floating Lyrics

Overlay lirik untuk lagu yang sedang diputar di Spotify. Dibuat dengan Python dan Tkinter, dengan panel gelap yang bisa digeser dan diubah ukurannya.

## Fitur

- Lirik sinkron per baris dari [LRCLIB](https://lrclib.net/).
- Fallback otomatis ke [Lyrica](https://github.com/thinkely/Lyrica) jika LRCLIB gagal, membatasi request, atau tidak menemukan lirik. Lyrica mencari dari sumber selain LRCLIB; timestamp per baris tetap digunakan jika tersedia.
- Highlight karaoke per kata, dengan timing yang **diperkirakan** dari panjang kata. LRCLIB menyediakan timing per baris, bukan per kata.
- Fallback ke lirik biasa jika lirik sinkron tidak tersedia.
- Window always-on-top, drag untuk memindahkan, dan resize dari tepi/sudut.
- Ukuran font mengikuti ukuran window.

## Persiapan

- Python 3.11 atau lebih baru, dengan Tkinter. Jalankan `python -m tkinter` untuk mengecek Tkinter.
- Koneksi internet, akun Spotify, dan aplikasi di [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
- Pemilik aplikasi Development Mode perlu Spotify Premium. Akun lain yang menggunakan aplikasi tersebut harus mengikuti pengaturan akses Spotify. Lihat [ketentuan Development Mode](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

Project ini ditujukan untuk desktop Windows. Efek acrylic dan kode Win32 sudah dihapus; platform desktop lain belum diverifikasi.

## Jalankan dari source

Setelah clone/download repository, buka terminal di folder project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.ini config.ini
```

Di Spotify Developer Dashboard, daftarkan redirect URI berikut **persis sama**:

```text
http://127.0.0.1:8765/callback
```

Spotify mengizinkan HTTP untuk alamat loopback eksplisit seperti `127.0.0.1`; lihat [panduan redirect URI](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).

Isi `client_id` dan `client_secret` milik aplikasi kamu di `config.ini`. Jangan mengedit kredensial di source Python. Kemudian:

```powershell
.\.venv\Scripts\python.exe -m spotify_lyrics
```

Browser akan dibuka untuk login dan memberikan izin membaca playback saat akses Spotify pertama kali diperlukan. Putar lagu di Spotify, lalu lirik akan dicari otomatis. `python index.py` juga tetap bisa digunakan sebagai launcher.

Di macOS/Linux, gunakan `.venv/bin/python` sebagai pengganti `.\.venv\Scripts\python.exe`. Beberapa distribusi Linux perlu paket Tkinter tambahan dari package manager sistem.

### Konfigurasi dan data lokal

`config.ini` dibaca dari root project, sehingga lokasi konfigurasi tidak bergantung pada folder terminal saat aplikasi dijalankan. Environment variable berikut akan menimpa nilai di file:

| Environment variable | Isi |
| --- | --- |
| `SPOTIPY_CLIENT_ID` | Client ID Spotify |
| `SPOTIPY_CLIENT_SECRET` | Client secret Spotify |
| `SPOTIPY_REDIRECT_URI` | Redirect URI; default `http://127.0.0.1:8765/callback` |
| `LYRICA_BASE_URL` | URL server Lyrica; default `https://test-0k.onrender.com`. Bisa diarahkan ke server sendiri, misalnya `http://127.0.0.1:9999` |

Fallback Lyrica memakai instance publik yang dicantumkan dalam [dokumentasi Lyrica](https://github.com/thinkely/Lyrica/blob/main/guide/USER_GUIDE.md). Ketersediaan instance dan sumber lirik dapat berubah. Timeout LRCLIB adalah 5 detik dan Lyrica 10 detik per request.

Token login disimpan di `.spotify_cache` pada folder yang sama dengan konfigurasi. `config.ini`, token, virtual environment, dan hasil build sudah diabaikan oleh `.gitignore`. Jangan sertakan file-file tersebut dalam issue, PR, atau ZIP yang dibagikan.

## Kontrol

| Aksi | Kontrol |
| --- | --- |
| Pindahkan overlay | Klik kiri dan drag bagian tengah |
| Ubah ukuran | Drag tepi atau sudut |
| Tutup aplikasi | Klik kanan pada overlay |

## Build Windows `.exe`

```powershell
.\build_exe.bat
```

Hasil build ada di `dist/SpotifyLyrics.exe`. Salin `config.example.ini` menjadi `config.ini` **di samping executable**, lalu isi kredensial sendiri. Konfigurasi dan token tidak dibundel ke executable. Folder tersebut harus bisa ditulis untuk menyimpan token dan log `spotify_lyrics.log`.

Script build memasang dependency development, termasuk PyInstaller. Aplikasi biasa hanya membutuhkan dependency di `requirements.txt`.

## Struktur project

```text
spotify_lyrics/
  __main__.py         # python -m spotify_lyrics
  app.py              # startup, queue UI, dan lifecycle worker
  config.py           # konfigurasi lokal/environment
  spotify_client.py   # OAuth dan metadata playback Spotify
  lyrics.py           # LRCLIB/Lyrica, parsing LRC, dan timing kata
  window.py           # tampilan Tkinter dan interaksi overlay
  worker.py           # polling Spotify dan pengiriman update
tests/                # test tanpa login Spotify atau network
.github/              # CI dan template kontribusi
index.py              # launcher kompatibilitas dan entry point build
config.example.ini    # template konfigurasi tanpa kredensial
requirements.txt      # dependency runtime
requirements-dev.txt  # dependency development/build
build_exe.bat         # build executable Windows
```

## Troubleshooting

- **Konfigurasi belum lengkap:** salin template dan isi kedua kredensial. Untuk `.exe`, letakkan `config.ini` di samping executable.
- **`Cannot find a usable init.tcl`:** instalasi Tcl/Tk milik Python tidak lengkap. Perbaiki/reinstall Python dengan dukungan Tcl/Tk, lalu buat ulang virtual environment. Script build mengecek Tkinter sebelum membuat executable.
- **Redirect URI error:** samakan alamat dan port di konfigurasi dengan Dashboard. Default port project ini adalah `8765`.
- **Akses Spotify ditolak:** periksa kredensial, Premium pemilik aplikasi, dan akses pengguna pada Dashboard. Error API muncul di terminal atau log executable.
- **Tidak ada lagu yang diputar:** aplikasi hanya membaca playback lagu; podcast/episode diabaikan.
- **Lirik tidak ditemukan:** LRCLIB dan Lyrica tidak menemukan lirik yang cocok dengan metadata lagu.
- **Layanan lirik gagal:** fallback Lyrica dicoba langsung setelah LRCLIB gagal. Jika keduanya gagal diakses, aplikasi mencoba ulang langsung sekali, lalu setiap 2 detik untuk kegagalan biasa.
- **LRCLIB membatasi request (429):** Lyrica dicoba terlebih dahulu. Jika fallback tidak menghasilkan lirik, aplikasi menunggu sesuai header `Retry-After`. Jika header tidak tersedia, jeda dimulai dari 60 detik dan bertambah sampai 15 menit jika masih gagal. Percobaan ulang otomatis mengambil lagu yang sedang aktif; mengganti lagu tidak melewati jeda.
- **Highlight kurang tepat:** timing per kata adalah estimasi. Lirik biasa tidak memiliki highlight sinkron.
- **Login ulang/ganti akun:** tutup aplikasi, hapus file lokal `.spotify_cache`, lalu jalankan kembali.

Untuk kontribusi dan perintah pengecekan kode, lihat [CONTRIBUTING.md](CONTRIBUTING.md).

Project ini tidak berafiliasi dengan Spotify atau LRCLIB.

# Kontribusi

Issue dan pull request boleh ditulis dalam bahasa Indonesia atau Inggris.

## Setup development

1. Fork dan clone repository, lalu buat branch untuk perubahan kamu.
2. Buat virtual environment seperti pada [README](README.md).
3. Pasang dependency development:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Login Spotify diperlukan untuk mencoba overlay secara langsung. Test otomatis menggunakan mock dan tidak memerlukan kredensial atau koneksi ke layanan eksternal.

## Sebelum membuka pull request

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Gunakan `python -m ruff format .` untuk merapikan format. CI menjalankan lint, format check, dan test pada Windows/Linux dengan Python 3.11 dan 3.14. Pengujian UI pada desktop tetap perlu dilakukan manual jika perubahan menyentuh `window.py`.

Pisahkan perubahan sesuai tanggung jawab modul. Worker mengirim update lewat queue; seluruh pemanggilan Tkinter dilakukan di thread UI. Pertahankan `index.py` sebagai launcher agar script build dan cara menjalankan lama tetap bekerja.

Untuk perubahan UI, cek drag, resize, always-on-top, klik kanan untuk menutup, dan highlight saat lagu pause/resume. Untuk perubahan build, jalankan `build_exe.bat` dan uji konfigurasi di samping executable.

Tuliskan masalah yang diselesaikan, perubahan perilaku, dan cara verifikasinya dalam PR. Jangan sertakan `config.ini`, `.spotify_cache`, kredensial, atau token dalam source, screenshot, maupun log. Jika melaporkan bug, sertakan versi Python, OS, langkah reproduksi, dan pesan error yang sudah disensor.

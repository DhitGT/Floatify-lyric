@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Membuat virtual environment...
    python -m venv .venv
    if errorlevel 1 exit /b 1
)

echo Memasang dependensi...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1

echo Memeriksa instalasi Tkinter...
.venv\Scripts\python.exe -c "import tkinter; root = tkinter.Tk(); root.withdraw(); root.destroy()"
if errorlevel 1 (
    echo Tkinter/Tcl/Tk tidak siap. Perbaiki instalasi Python sebelum membuild aplikasi.
    exit /b 1
)

echo Membuild SpotifyLyrics.exe...
.venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name SpotifyLyrics ^
    index.py

if errorlevel 1 exit /b 1

echo.
echo Selesai: dist\SpotifyLyrics.exe
echo Salin config.example.ini ke dist\config.ini lalu isi kredensial Spotify kamu.
endlocal

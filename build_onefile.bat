@echo off
setlocal
cd /d "%~dp0"

echo [Annota] Portable Windows build (single EXE)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
python tools\make_icons.py
if errorlevel 1 goto :fail
python -m compileall -q main.py tests tools
if errorlevel 1 goto :fail
python -m pytest -q
if errorlevel 1 goto :fail

if exist build rmdir /s /q build
if exist dist\Annota.exe del /q dist\Annota.exe
pyinstaller --noconfirm --clean --noconsole --onefile --name Annota --icon assets\annota.ico --add-data "assets;assets" --hidden-import ctypes --hidden-import json --hidden-import os --hidden-import platform --hidden-import tempfile --hidden-import dataclasses --hidden-import datetime --hidden-import pathlib --hidden-import typing --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --hidden-import pynput --hidden-import winreg main.py
if errorlevel 1 goto :fail
powershell -NoProfile -Command "$p='dist\Annota.exe'; (Get-FileHash $p -Algorithm SHA256).Hash + '  Annota.exe' | Set-Content 'dist\Annota.exe.sha256'"
if errorlevel 1 goto :fail

echo.
echo Build complete: dist\Annota.exe
echo Note: one-file startup is slower because Windows extracts bundled files at launch.
exit /b 0

:fail
echo [Annota] Build failed.
exit /b 1

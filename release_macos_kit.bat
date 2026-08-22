@echo off
setlocal
cd /d "%~dp0"

set "VERSION=0.2.8"
set "RELEASE_DIR=releases\v%VERSION%"
set "STAGE=%RELEASE_DIR%\Annota-v%VERSION%-macOS-Build-Kit"
set "ZIP=%RELEASE_DIR%\Annota-v%VERSION%-macOS-Build-Kit.zip"
set "SHA=%ZIP%.sha256"

echo [Annota] Packaging macOS build kit v%VERSION%

if exist "%STAGE%" rmdir /s /q "%STAGE%"
if exist "%ZIP%" del /q "%ZIP%"
if exist "%SHA%" del /q "%SHA%"
mkdir "%STAGE%" >nul 2>nul
mkdir "%STAGE%\assets" >nul 2>nul
mkdir "%STAGE%\tests" >nul 2>nul
mkdir "%STAGE%\tools" >nul 2>nul

copy /Y "main.py" "%STAGE%\main.py" >nul
copy /Y "requirements.txt" "%STAGE%\requirements.txt" >nul
copy /Y "requirements-dev.txt" "%STAGE%\requirements-dev.txt" >nul
copy /Y "pyproject.toml" "%STAGE%\pyproject.toml" >nul
copy /Y "README.md" "%STAGE%\README.md" >nul
copy /Y "QA.md" "%STAGE%\QA.md" >nul
copy /Y "LICENSE" "%STAGE%\LICENSE" >nul
copy /Y "MACOS_RELEASE.md" "%STAGE%\MACOS_RELEASE.md" >nul
copy /Y "build_macos.sh" "%STAGE%\build_macos.sh" >nul
copy /Y "release_macos.sh" "%STAGE%\release_macos.sh" >nul
xcopy "assets\*" "%STAGE%\assets\" /E /I /Y >nul
if errorlevel 1 goto :fail
xcopy "tests\*.py" "%STAGE%\tests\" /I /Y >nul
if errorlevel 1 goto :fail
xcopy "tools\*.py" "%STAGE%\tools\" /I /Y >nul
if errorlevel 1 goto :fail
copy /Y "tools\annota_hotkey.swift" "%STAGE%\tools\annota_hotkey.swift" >nul
if errorlevel 1 goto :fail

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGE%' -DestinationPath '%ZIP%' -CompressionLevel Optimal -Force"
if errorlevel 1 goto :fail
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%ZIP%'; (Get-FileHash $p -Algorithm SHA256).Hash + '  ' + [IO.Path]::GetFileName($p) | Set-Content '%SHA%'"
if errorlevel 1 goto :fail
rmdir /s /q "%STAGE%"

echo.
echo macOS build kit complete:
echo   %ZIP%
echo   %SHA%
exit /b 0

:fail
if exist "%STAGE%" rmdir /s /q "%STAGE%"
echo [Annota] macOS build kit packaging failed.
exit /b 1

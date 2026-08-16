@echo off
setlocal
cd /d "%~dp0"

set "VERSION=0.2.0"
set "RELEASE_DIR=releases\v%VERSION%"
set "STAGE=%RELEASE_DIR%\Annota-v%VERSION%-Windows-x64"
set "ZIP=%RELEASE_DIR%\Annota-v%VERSION%-Windows-x64.zip"
set "SHA=%ZIP%.sha256"

echo [Annota] Packaging Windows x64 release v%VERSION%

if not exist "dist\Annota\Annota.exe" (
  echo Missing dist\Annota\Annota.exe. Run build.bat first.
  exit /b 1
)

if exist "%STAGE%" rmdir /s /q "%STAGE%"
if exist "%ZIP%" del /q "%ZIP%"
if exist "%SHA%" del /q "%SHA%"
mkdir "%STAGE%" >nul 2>nul

xcopy "dist\Annota\*" "%STAGE%\" /E /I /Y >nul
if errorlevel 1 goto :fail
copy /Y "README.md" "%STAGE%\README.md" >nul
copy /Y "LICENSE" "%STAGE%\LICENSE" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGE%' -DestinationPath '%ZIP%' -CompressionLevel Optimal -Force"
if errorlevel 1 goto :fail
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%ZIP%'; (Get-FileHash $p -Algorithm SHA256).Hash + '  ' + [IO.Path]::GetFileName($p) | Set-Content '%SHA%'"
if errorlevel 1 goto :fail
rmdir /s /q "%STAGE%"

echo.
echo Windows release package complete:
echo   %ZIP%
echo   %SHA%
exit /b 0

:fail
if exist "%STAGE%" rmdir /s /q "%STAGE%"
echo [Annota] Windows release packaging failed.
exit /b 1

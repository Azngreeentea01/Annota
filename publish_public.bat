@echo off
setlocal
cd /d "%~dp0"

echo [Annota] Publishing public GitHub repository...
where gh >nul 2>nul
if errorlevel 1 (
  echo GitHub CLI (gh) was not found.
  exit /b 1
)

gh auth status
if errorlevel 1 (
  echo GitHub CLI is not authenticated.
  exit /b 1
)

if not exist ".git" (
  git init
  if errorlevel 1 exit /b 1
  git branch -M main
)

git add .
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Initial Annota desktop annotation app"
  if errorlevel 1 exit /b 1
)

git remote get-url origin >nul 2>nul
if errorlevel 1 (
  gh repo create Annota --public --source=. --remote=origin --push --description "Lightweight desktop annotation bridge for Codex and ChatGPT visual feedback"
  if errorlevel 1 exit /b 1
) else (
  git push -u origin main
  if errorlevel 1 exit /b 1
)

echo.
echo Public repository published.
gh repo view --web
exit /b 0

@echo off
echo ========================================
echo   Continuity - Push to GitHub
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] Initializing git repository...
git init
if errorlevel 1 (
    echo ERROR: Git not found. Install Git first.
    echo Download: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [2/5] Adding files...
git add .

echo [3/5] Creating commit...
git commit -m "Initial commit: Continuity - AI conversation memory"

echo [4/5] Creating GitHub repository...
gh repo create continuity --public --description "AI conversation memory - never lose the thread. Works with any AI provider." --source . --push
if errorlevel 1 (
    echo.
    echo Could not create repo automatically.
    echo Do it manually:
    echo   1. Go to https://github.com/new
    echo   2. Name: continuity
    echo   3. Create repository
    echo   4. Run: git remote add origin https://github.com/YOUR_USERNAME/continuity.git
    echo   5. Run: git push -u origin main
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Done! Repository created and pushed.
echo ========================================
pause

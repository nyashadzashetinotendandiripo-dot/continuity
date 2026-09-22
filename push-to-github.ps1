# Push Continuity to GitHub
# Run this script after Git is installed

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Continuity - Push to GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to script directory
Set-Location $PSScriptRoot

# Check if git is available
try {
    $gitVersion = & git --version 2>&1
    Write-Host "Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git not installed." -ForegroundColor Red
    Write-Host "Install from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "Or run: winget install Git.Git" -ForegroundColor Yellow
    exit 1
}

# Check if gh CLI is available
try {
    $ghVersion = & gh --version 2>&1
    Write-Host "GitHub CLI found: $ghVersion" -ForegroundColor Green
} catch {
    Write-Host "GitHub CLI not found." -ForegroundColor Yellow
    Write-Host "Install from: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host "Or run: winget install GitHub.cli" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[1/5] Initializing git repository..." -ForegroundColor Yellow
git init

Write-Host "[2/5] Adding files..." -ForegroundColor Yellow
git add .

Write-Host "[3/5] Creating commit..." -ForegroundColor Yellow
git commit -m "Initial commit: Continuity - AI conversation memory"

Write-Host "[4/5] Creating GitHub repository..." -ForegroundColor Yellow
try {
    gh repo create continuity --public --description "AI conversation memory - never lose the thread. Works with any AI provider." --source . --push
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Done! Repository created and pushed." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Could not create repo automatically." -ForegroundColor Yellow
    Write-Host "Do it manually:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://github.com/new" -ForegroundColor White
    Write-Host "  2. Name: continuity" -ForegroundColor White
    Write-Host "  3. Create repository" -ForegroundColor White
    Write-Host "  4. Run: git remote add origin https://github.com/YOUR_USERNAME/continuity.git" -ForegroundColor White
    Write-Host "  5. Run: git push -u origin main" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"

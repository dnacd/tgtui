$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."

Write-Host "---------------------------------------" -ForegroundColor Cyan
Write-Host "  Installing TGT (Telegram Textual TUI) " -ForegroundColor Cyan
Write-Host "---------------------------------------" -ForegroundColor Cyan

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed. Please install it from python.org."
    exit 1
}

if (!(Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "pipx not found. Installing pipx..." -ForegroundColor Yellow
    python -m pip install --user pipx | Out-Null
    python -m pipx ensurepath | Out-Null
    
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
}

Write-Host "Installing package and dependencies..." -ForegroundColor Yellow
pipx install "$ProjectRoot" --force --include-deps | Out-Null

Write-Host "---------------------------------------" -ForegroundColor Green
Write-Host "Success! TGT is now installed." -ForegroundColor Green
Write-Host "Run 'tgt --help' to get started." -ForegroundColor Green
Write-Host "---------------------------------------" -ForegroundColor Green

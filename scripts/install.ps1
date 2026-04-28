$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."

Write-Host "---------------------------------------" -ForegroundColor Cyan
Write-Host "  Installing TGT (Telegram Textual TUI) " -ForegroundColor Cyan
Write-Host "---------------------------------------" -ForegroundColor Cyan

$PythonVersion = & python --version 2>&1
$IsOldPython = $true
if ($PythonVersion -match "Python 3\.(1[1-9]|[2-9])") { $IsOldPython = $false }

if (!(Get-Command python -ErrorAction SilentlyContinue) -or $IsOldPython) {
    Write-Host "Python 3.11+ not found. Attempting to install via winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.11 --scope machine
    Write-Host "Please restart the terminal after Python installation and run the script again." -ForegroundColor Red
    exit 1
}

if (!(Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "pipx not found. Installing pipx..." -ForegroundColor Yellow
    python -m pip install --user pipx
    python -m pipx ensurepath
    Write-Host "Please restart the terminal after pipx installation and run the script again." -ForegroundColor Red
    exit 1
}

Write-Host "Installing package and dependencies..." -ForegroundColor Yellow
pipx install "$ProjectRoot" --force --include-deps --python python

Write-Host "Building and injecting Rust module (ansi-render-native)..." -ForegroundColor Yellow
if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: Rust (cargo) not found. ANSI rendering might not work." -ForegroundColor Red
    Write-Host "Please install Rust: https://rustup.rs/" -ForegroundColor Yellow
} else {
    # Install maturin in the pipx environment
    pipx inject telegram-textual-tui maturin
    
    # Go to the tool directory and build/install it into the pipx venv
    Push-Location "$ProjectRoot\telegram_textual_tui\ansi_renderer"
    pipx runpip telegram-textual-tui install .
    if (Test-Path "target") { Remove-Item -Recurse -Force "target" }
    Pop-Location
}

Write-Host "---------------------------------------" -ForegroundColor Green
Write-Host "Success! TGT is now installed with ANSI support." -ForegroundColor Green
Write-Host "Run 'tgt --help' to get started." -ForegroundColor Green
Write-Host "---------------------------------------" -ForegroundColor Green

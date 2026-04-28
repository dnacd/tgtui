#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "---------------------------------------"
echo "  Installing TGT (Telegram Textual TUI) "
echo "---------------------------------------"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install it first."
    exit 1
fi

if ! command -v pipx &> /dev/null; then
    echo "pipx not found. Installing pipx via pip..."
    python3 -m pip install --user pipx &> /dev/null
    python3 -m pipx ensurepath &> /dev/null
    export PATH="$PATH:$HOME/.local/bin"
fi

echo "Installing package and dependencies..."
python3 -m pipx install "$PROJECT_ROOT" --force --include-deps

echo "---------------------------------------"
echo "Success! TGT is now installed."
echo "Run 'tgt --help' to get started."
echo "---------------------------------------"

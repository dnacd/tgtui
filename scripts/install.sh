#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "---------------------------------------"
echo "  Installing TGT (Telegram Textual TUI) "
echo "---------------------------------------"

# 1. Ensure Rust is in PATH
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
fi

# 2. Check Python version (3.11+ preferred, 3.8+ required)
PYTHON_CMD="python3"
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
fi

# 3. Ensure Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "Rust not found. Installing via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 4. Pipx installation/update
if ! command -v pipx &> /dev/null; then
    $PYTHON_CMD -m pip install --user pipx
    $PYTHON_CMD -m pipx ensurepath
    export PATH="$PATH:$HOME/.local/bin"
fi

echo "Installing package and core dependencies..."
pipx install "$PROJECT_ROOT" --force --include-deps --python "$PYTHON_CMD"

echo "Injecting mandatory UI dependencies..."
# Ensure Pillow and Rich are correctly installed in the venv
pipx inject telegram-textual-tui Pillow rich --force

echo "Building and injecting Rust module..."
pipx inject telegram-textual-tui maturin --force

# Build and install the rust tool into the same venv
pushd "$PROJECT_ROOT/telegram_textual_tui/ansi_renderer" > /dev/null
pipx runpip telegram-textual-tui install .
rm -rf target
popd > /dev/null

echo "---------------------------------------"
echo "Success! TGT is now installed."
echo "Run 'tgt --help' to get started."
echo "---------------------------------------"

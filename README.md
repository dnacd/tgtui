# TGT (Telegram Textual TUI)

TGT is a local-first Telegram client for people who love the terminal aesthetic. It's not just a CLI wrapper; it's a cozy, high-fidelity space for your chats, inspired by the gritty feel of old-school computer interfaces and the sleek chat terminal from **Warframe** :D
  
I built this because I wanted a Telegram client that feels like a piece of hardware from a sci-fi movie—fast, keyboard-driven, and visually alive.

## The Vibe

- **Truecolor ANSI Magic**: We use a native Rust engine to turn profile photos into high-res ANSI art. It's not just ASCII; it's full-color terminal painting.
- **Sci-Fi Identicons**: No profile photo? No problem. TGT generates unique, symmetric geometric patterns for every user, so everyone has a distinct visual identity that fits the aesthetic.
- **Keyboard-First Flow**: Forget the mouse. Everything is mapped to your fingers, making it feel like you're actually "operating" a terminal.
- **Fast & Lightweight**: It's built with Python Textual and Rust, designed to be snappy and stay out of your way. No web-view bloat here.

## What's under the hood?

- **MTProto Power**: Connects directly to Telegram via Telethon.
- **Native Rust Renderer**: A custom-built library (PyO3) that handles the heavy lifting of image processing and ANSI encoding.
- **Smart Caching**: Avatars and assets are cached locally, so they load instantly after the first time.
- **Private by Design**: Your keys and sessions stay on your machine. Period.

## Getting Around (Keyboard Only)

### Moving the Focus
- **Tab / Shift+Tab**: Cycle through everything.
- **Ctrl+L**: Jump straight to the chat list.
- **Ctrl+S**: Jump to search.
- **Esc**: Go back or focus the message input.

### Chatting
- **Arrows**: Navigate the list.
- **Enter**: Open a chat.
- **PageUp / PageDown**: Scroll through history.
- **r**: Send a quick reaction to the last message.
- **l**: Force refresh the chat list.

### Profiles & Screens
- **p**: Look at your own profile.
- **u**: See who you're talking to.
- **b**: Back to the terminal.
- **Ctrl+Q**: Shut it down.

## Installation

The installation scripts handle the Rust compilation and dependency injection for you.

### Linux / macOS
```bash
git clone https://github.com/dnacd/tgtui.git
cd tgtui
chmod +x scripts/install.sh
./scripts/install.sh
```

### Windows
```powershell
git clone https://github.com/dnacd/tgtui.git
cd tgtui
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```
*Note: Make sure you have [Rust](https://rustup.rs/) installed so we can build the ANSI engine.*

## Quick Start

1. `tgt init` — Set up your API credentials (from my.telegram.org).
2. `tgt login` — Sign in to Telegram.
3. `tgt clean` — Clear the local avatar cache and logs.
4. `tgt tui` — Enter the terminal.

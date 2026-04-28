# tgt (Telegram Textual TUI)

A local-first Telegram terminal client built with [Textual](https://textual.textualize.io/) and [Telethon](https://docs.telethon.dev/).

## Status

**Early MVP.**

Currently supported:
- Unified CLI (`tgt`)
- Secure local login
- Dialog list (chats, groups, channels)
- Basic message viewing
- Search in chats
- Media placeholders

## Security & Privacy

- **Local-first**: All data stays on your machine.
- **Direct Connection**: Connects directly to Telegram via Telethon.
- **No Telemetry**: No analytics or tracking.
- **No Backend**: Your data is never sent to our servers.

## Installation

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

## Getting Started

1. **Initialize**:
   ```bash
   tgt init
   ```
   This will open `my.telegram.org` and help you set up your API credentials.

2. **Login**:
   ```bash
   tgt login
   ```

3. **Run TUI**:
   ```bash
   tgt tui
   ```

## Keyboard Shortcuts (Keyboard-Only Mode)

The application is designed to be fully navigable via keyboard.

### Global
- `Ctrl+Q` : Quit application

### Navigation & Focus
- `Ctrl+L` : Focus Chat List
- `Ctrl+I` or `Esc` : Focus Message Input
- `PageUp` / `PageDown` : Scroll messages
- `p` : Show My Profile
- `u` : Show Partner's Profile (when in chat)
- `b` or `Esc` : Back (from Profile screens)

### Search
- `/` or `Ctrl+S` : Focus Search bar

### Actions
- `r` : React to the last message in current chat
- `l` : Reload all dialogs (refresh chat list)

## Commands

- `tgt init` - Setup API ID and API Hash
- `tgt login` - Authenticate with Telegram
- `tgt tui` - Launch the terminal interface
- `tgt session` - Show session file path
- `tgt logout` - Logout and remove session
- `tgt doctor` - Run system diagnostics

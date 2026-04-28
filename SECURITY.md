# Security Policy

`tgt` is a local-first Telegram client.

## Data Storage

- **Session Data**: Your Telegram session is stored locally in `~/.telegram_textual_tui/`.
- **Credentials**: API credentials are stored in `~/.telegram_textual_tui/config.json`.
- **No Remote Storage**: We do not have a backend. Your data never leaves your machine except to communicate with Telegram's servers.

## Network Activity

`tgt` only communicates with Telegram's official servers via the Telethon library. It does not send telemetry, crash reports, or any other data to any third-party servers.

## Recommendations

- Never share your `session` file or `config.json` with anyone.
- Only run `tgt` from trusted sources.
- If you use a shared machine, always run `tgt logout` after use.

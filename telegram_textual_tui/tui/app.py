"""
Main Textual Application for Telegram Textual TUI.
Orchestrates the lifecycle of the application and coordinates between screens.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from telegram_textual_tui.core.client import TelegramManager
from telegram_textual_tui.core.config import load_application_configuration
from telegram_textual_tui.tui.config.keymap import Keymap
from telegram_textual_tui.tui.screens.login import LoginScreen
from telegram_textual_tui.tui.screens.main import MainScreen


class TGTApp(App):
    """
    The main Application class for the Telegram Textual TUI.
    Handles global state, configuration, and top-level navigation.
    """

    CSS = """
    #sidebar {
        width: 35;
        border-right: heavy $primary;
        background: $surface;
    }
    #chat-area {
        width: 1fr;
        background: $background;
    }
    #messages {
        height: 1fr;
        border-bottom: heavy $primary;
        padding: 1 2;
    }
    #message-input {
        margin: 0;
        border: none;
        height: 3;
    }
    #chat-search {
        margin: 0;
        border: none;
        border-bottom: heavy $primary;
    }
    ChatItem {
        layout: horizontal;
        height: 3;
        padding: 0 1;
        margin: 0 1;
        border: none;
    }
    ChatItem:hover {
        background: $boost;
    }
    ChatItem.--highlight {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    .chat-avatar {
        width: 2;
        height: 1;
        margin: 1 1 0 0;
        text-align: center;
        text-style: bold;
    }
    .avatar-blue { color: #4a90e2; }
    .avatar-green { color: #7ed321; }
    .avatar-yellow { color: #f5a623; }
    .avatar-magenta { color: #bd10e0; }
    .avatar-cyan { color: #50e3c2; }
    .avatar-white { color: #9b9b9b; }
    
    #messages:focus {
        border-bottom: heavy $primary;
    }
    
    .chat-title {
        width: 1fr;
        height: 1;
        content-align: left middle;
        text-overflow: ellipsis;
        margin-top: 1;
    }
    .chat-unread {
        width: auto;
        min-width: 3;
        height: 1;
        color: $accent;
        background: $surface;
        content-align: right middle;
        text-style: bold;
        margin-top: 1;
        padding: 0 1;
    }
    #login-form, #profile-container {
        width: 50;
        margin: 4 4;
        padding: 1 2;
        border: heavy $primary;
    }
    #login-title, #profile-title {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        text-style: bold;
        color: $accent;
    }
    #profile-details {
        margin-bottom: 1;
        padding: 1;
    }
    Input {
        margin-bottom: 1;
        border: tall $primary;
    }
    Input:focus {
        border: tall $accent;
    }
    Tabs {
        height: 3;
        border-bottom: solid $primary;
    }
    """

    BINDINGS = Keymap.GLOBAL

    def __init__(self, *args, **kwargs):
        """
        Initialize the application state, configuration, and manager components.
        """
        super().__init__(*args, **kwargs)
        self.configuration = load_application_configuration()
        self.telegram_manager: TelegramManager | None = None
        if self.configuration:
            self.telegram_manager = TelegramManager(self.configuration)

    async def on_mount(self) -> None:
        """
        Establish Telegram connection and determine the initial screen based on authentication.
        """
        if not self.telegram_manager:
            await self.push_screen(LoginScreen())
        else:
            await self.telegram_manager.connect_to_telegram()
            if await self.telegram_manager.is_client_authorized():
                await self.push_screen(MainScreen())
            else:
                await self.push_screen(LoginScreen())

    def compose(self) -> ComposeResult:
        """
        Compose the main application layout including the global header and footer.
        """
        yield Header()
        yield Footer()

def main():
    """Entry point for the TUI application."""
    app = TGTApp()
    app.run()

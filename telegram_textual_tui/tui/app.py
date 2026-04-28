"""
Main Textual Application for Telegram Textual TUI.
Orchestrates the lifecycle of the application and coordinates between screens.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from telegram_textual_tui.core.client import TelegramManager
from telegram_textual_tui.core.config import load_application_configuration
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
        border-right: solid $primary;
    }
    #chat-area {
        width: 1fr;
    }
    #messages {
        height: 1fr;
        border-bottom: solid $primary;
        padding: 1;
    }
    #message-input {
        margin: 0;
        border: none;
    }
    #chat-search {
        margin: 0;
        border: none;
        border-bottom: solid $primary;
    }
    ChatItem {
        layout: horizontal;
        height: 1;
        padding: 0 1;
        overflow: hidden;
    }
    .chat-title {
        width: 1fr;
        height: 1;
        content-align: left middle;
    }
    .chat-unread {
        width: auto;
        min-width: 3;
        height: 1;
        color: $accent;
        content-align: right middle;
        text-style: bold;
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
    }
    #profile-details {
        margin-bottom: 1;
        padding: 1;
    }
    Input {
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

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

"""
Main application module for the Telegram Textual TUI.

This module initializes the Textual environment, manages global application 
state (including the Telegram manager), handles routing between different 
screens (Login, Main, Profile), and defines the global visual style (CSS).
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from telegram_textual_tui.core.config import load_application_configuration
from telegram_textual_tui.core.client import TelegramManager
from telegram_textual_tui.tui.screens.login import LoginScreen
from telegram_textual_tui.tui.screens.main import MainScreen
from telegram_textual_tui.tui.screens.profile import ProfileScreen


class TGTApp(App):
    """
    The core Application class that coordinates between Telegram and the TUI.
    
    Attributes:
        configuration: The loaded application settings (API ID, Hash, etc.).
        telegram_manager: Wrapper for the Telethon client and avatar system.
    """

    CSS = """
    Screen {
        background: $background;
    }
    
    /* Profile Screen Layout */
    Screen#ProfileScreen {
        align: center middle;
    }
    
    #profile-container {
        width: 54;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #profile-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        background: $primary;
        color: $text;
        margin-bottom: 1;
    }
    
    #profile-avatar {
        width: 50;
        height: 25;
        margin: 1 0;
    }
    
    #profile-details {
        margin-top: 1;
        border: solid $primary;
        padding: 1;
    }
    
    #profile-back-btn {
        margin-top: 1;
        width: 100%;
    }
    
    /* Main Screen Sidebar and Chat Area */
    #sidebar {
        width: 40;
        height: 100%;
        border-right: solid $primary;
    }
    
    #chat-area {
        width: 1fr;
        height: 100%;
    }
    
    ChatItem {
        layout: horizontal;
        height: 4;
        padding: 0 1;
        margin: 1 0 0 0;
        border: none;
        content-align: left middle;
    }
    
    ChatItem:hover {
        background: $boost;
    }
    
    ChatItem.--highlight {
        background: $accent;
        color: $text;
        text-style: bold;
    }

    AnsiImage {
        content-align: center middle;
    }
    
    .chat-avatar-mini {
        width: 16;
        height: 4;
        margin-right: 1;
    }
    
    .chat-title {
        width: 1fr;
        height: 100%;
        content-align: left middle;
    }
    
    .chat-unread {
        width: auto;
        min-width: 3;
        height: 100%;
        background: $accent;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

    #message-input {
        width: 100%;
        margin: 0;
        border: none;
        background: $boost;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, *args, **kwargs):
        """
        Set up the application state and load local configuration.
        """
        super().__init__(*args, **kwargs)
        self.configuration = load_application_configuration()
        self.telegram_manager: Optional[TelegramManager] = None
        if self.configuration:
            self.telegram_manager = TelegramManager(self.configuration)

    async def on_mount(self) -> None:
        """
        Establish connection to Telegram upon application startup.
        
        This method checks for an active session and authenticates the user.
        If no session is found, it redirects the user to the Login screen.
        """
        from telegram_textual_tui.core.avatars import ansi_render_native
        if ansi_render_native is None:
            self.notify("ANSI Render module not loaded!", severity="error")

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
        Define the global UI components like the Header and Footer.
        """
        yield Header()
        yield Footer()

    async def action_show_user_profile(self, user_id: str, msg_id: str = "") -> None:
        """
        Navigate to a specific user's profile screen.
        
        This action is globally available and can be triggered by clicking 
        on user names within message logs.

        Args:
            user_id: The unique Telegram user ID (as string).
            msg_id: An optional message ID to ensure the clickable link is unique.
        """
        try:
            uid = int(user_id)
            await self.push_screen(ProfileScreen(user_id=uid))
        except (ValueError, TypeError):
            pass


def main():
    """
    Application entry point. Initializes and runs the TUI.
    """
    app = TGTApp()
    app.run()

"""
Login screen for the Telegram Textual TUI.
Provides an interactive authentication form for Telegram.
"""

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label

if TYPE_CHECKING:
    from telegram_textual_tui.tui.app import TGTApp


class LoginScreen(Screen):
    """
    Screen providing an interactive authentication form for Telegram.
    """

    def compose(self) -> ComposeResult:
        """
        Compose the authentication form layout.
        """
        yield Container(
            Vertical(
                Label("Telegram Login", id="login-title"),
                Input(placeholder="API ID", id="api-id"),
                Input(placeholder="API Hash", id="api-hash", password=True),
                Input(placeholder="Phone (+79990000000)", id="phone"),
                Input(placeholder="Code", id="code"),
                Input(placeholder="2FA Password", id="password", password=True),
                Button("Login", variant="primary", id="login-btn"),
                id="login-form",
            )
        )

    def on_mount(self) -> None:
        """
        Pre-fill the authentication form if existing configuration is found.
        """
        application_instance: TGTApp = self.app
        if application_instance.configuration:
            self.query_one("#api-id", Input).value = str(application_instance.configuration.api_id)
            self.query_one("#api-hash", Input).value = application_instance.configuration.api_hash
            self.query_one("#phone").focus()

"""
Profile screen for the Telegram Textual TUI.
Displays detailed information about a Telegram user.
"""

from typing import TYPE_CHECKING, Optional

from telethon.tl.functions.users import GetFullUserRequest
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from telegram_textual_tui.tui.widgets.ansi_image import AnsiImage

if TYPE_CHECKING:
    from telegram_textual_tui.tui.app import TGTApp


class ProfileScreen(Screen):
    """
    Screen displaying user profile information including bio and contact details.
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.pop_screen", "Back"),
    ]

    def __init__(self, user_id: Optional[int] = None, *args, **kwargs):
        """
        Initialize the profile screen for a specific user.

        Args:
            user_id: The unique Telegram ID of the user. If None, the current user's profile is shown.
        """
        super().__init__(*args, **kwargs)
        self.target_user_id = user_id

    def compose(self) -> ComposeResult:
        """
        Create the visual structure for the profile screen.
        """
        yield Container(
            Vertical(
                Label("User Profile", id="profile-title"),
                AnsiImage(id="profile-avatar"),
                Static(id="profile-details"),
                Button("Back", variant="primary", id="profile-back-btn"),
                id="profile-container"
            )
        )

    async def on_mount(self) -> None:
        """
        Fetch and display user profile details upon mounting the screen.
        """
        application_instance: TGTApp = self.app
        if not application_instance.telegram_manager:
            return

        try:
            if self.target_user_id:
                user_entity = await application_instance.telegram_manager.client.get_entity(self.target_user_id)
            else:
                user_entity = await application_instance.telegram_manager.get_authenticated_user_details()

            # Load avatar in background
            first_name = getattr(user_entity, 'first_name', '') or ''
            initials = (first_name[0] if first_name else "?").upper()
            avatar_widget = self.query_one("#profile-avatar", AnsiImage)
            avatar_widget.fallback_text = initials
            self.run_worker(self._load_avatar(user_entity))

            full_user_data = await application_instance.telegram_manager.client(GetFullUserRequest(user_entity.id))
            
            details_widget = self.query_one("#profile-details", Static)
            
            last_name = getattr(user_entity, 'last_name', '') or ''
            display_name = f"{first_name} {last_name}".strip()
            username_label = f"@{user_entity.username}" if getattr(user_entity, 'username', None) else "None"
            phone_label = f"+{getattr(user_entity, 'phone', 'Unknown')}" if getattr(user_entity, 'phone', None) else "Private"
            user_biography = full_user_data.full_user.about or "No bio"

            formatted_content = [
                f"[bold cyan]Name:[/bold cyan] {display_name}",
                f"[bold cyan]Username:[/bold cyan] {username_label}",
                f"[bold cyan]Phone:[/bold cyan] {phone_label}",
                f"[bold cyan]Bio:[/bold cyan] {user_biography}",
                "\n[dim]Press Esc or B to go back[/dim]"
            ]
            
            details_widget.update("\n".join(formatted_content))
        except Exception as error:
            self.query_one("#profile-details", Static).update(f"[red]Error loading profile: {error}[/red]")

    async def _load_avatar(self, user_entity) -> None:
        """Load and render the user avatar."""
        avatar_manager = self.app.telegram_manager.avatar_manager
        avatar_data = await avatar_manager.get_avatar(user_entity, size="large")
        avatar_widget = self.query_one("#profile-avatar", AnsiImage)
        if avatar_data:
            avatar_widget.update_image(avatar_data)
        else:
            avatar_widget.set_loading(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button interaction events.
        """
        if event.button.id == "profile-back-btn":
            self.app.pop_screen()

"""
Centralized keyboard mapping configuration for the Telegram Textual TUI.
Provides localized bindings for both English and Russian layouts.
"""

from typing import List, Optional
from textual.binding import Binding


def create_localized_binding(
    en_key: str,
    ru_key: Optional[str],
    action: str,
    description: str,
    show: bool = True,
    priority: bool = False,
) -> List[Binding]:
    """Create a pair of bindings for English and Russian layouts."""
    bindings = [Binding(en_key, action, description, show=show, priority=priority)]
    if ru_key:
        bindings.append(Binding(ru_key, action, description, show=False, priority=priority))
    return bindings


class Keymap:
    """Groups of localized bindings for the application."""

    GLOBAL = [
        *create_localized_binding("ctrl+q", None, "quit", "Quit"),
    ]

    MAIN_SCREEN = [
        *create_localized_binding("/", ".", "focus_search", "Search"),
        *create_localized_binding("ctrl+s", "ctrl+ы", "focus_search", "Search", show=False),
        *create_localized_binding("ctrl+l", "ctrl+д", "focus_chat_list", "Chats"),
        *create_localized_binding("ctrl+i", "ctrl+ш", "focus_message_input", "Input"),
        *create_localized_binding("tab", None, "focus_message_input", "Input", show=False),
        *create_localized_binding("escape", None, "focus_message_input", "Input", show=False),
        *create_localized_binding("p", "з", "show_my_profile", "My Profile"),
        *create_localized_binding("u", "г", "show_partner_profile", "User Profile"),
        *create_localized_binding("r", "к", "react_to_last_message", "React Last"),
        *create_localized_binding("l", "д", "reload_all_dialogs", "Reload"),
        Binding("pageup", "scroll_messages_up", "Scroll Up", show=False),
        Binding("pagedown", "scroll_messages_down", "Scroll Down", show=False),
    ]

    PROFILE_SCREEN = [
        Binding("escape", "app.pop_screen", "Back"),
        *create_localized_binding("b", "и", "app.pop_screen", "Back"),
    ]

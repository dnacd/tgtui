"""
Widget for displaying the list of Telegram dialogs.
"""

from typing import Any
from textual.widgets import ListView, ListItem, Label
from textual.app import ComposeResult
from telegram_textual_tui.utils.formatters import get_telegram_entity_title


class ChatItem(ListItem):
    """
    A single interactive item within the chat list sidebar.
    """

    def __init__(self, dialog: Any):
        """
        Initialize a chat list item with Telegram dialog data.

        Args:
            dialog: A Telethon Dialog object containing chat and entity metadata.
        """
        super().__init__()
        self.dialog = dialog
        self.title_text = get_telegram_entity_title(self.dialog.entity)
        self.search_text = self.title_text.lower()

    def compose(self) -> ComposeResult:
        """
        Create the visual structure for the chat item.
        """
        yield Label(self.title_text, classes="chat-title", markup=False)
        if self.dialog.unread_count > 0:
            yield Label(str(self.dialog.unread_count), classes="chat-unread")



class ChatList(ListView):
    """
    List view containing Telegram chats.
    """
    pass

"""
Widget for displaying the list of Telegram dialogs with filtering capabilities.
"""

from typing import Any, Callable, Dict, Optional

from telethon.tl.types import Channel, Chat, User
from textual.app import ComposeResult
from textual.widgets import Label, ListItem, ListView

from telegram_textual_tui.utils.formatters import get_telegram_entity_title


class ChatItem(ListItem):
    """
    A single interactive item within the chat list sidebar.
    """

    def __init__(self, dialog: Any) -> None:
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
    List view containing Telegram chats with category and search filtering.
    """

    FILTER_MAP: Dict[str, Callable[[Any], bool]] = {
        "all": lambda _: True,
        "private": lambda entity: isinstance(entity, User) and not entity.bot,
        "groups": lambda entity: isinstance(entity, (Chat, Channel)),
        "bots": lambda entity: isinstance(entity, User) and entity.bot,
    }

    def apply_filter(self, category: str, search_term: str) -> None:
        """
        Filter the list items based on the active category and search term.
        
        Args:
            category: The active tab ID (all, private, groups, bots).
            search_term: The current text in the search input.
        """
        filter_func = self.FILTER_MAP.get(category, lambda _: True)
        term = search_term.lower()
        
        first_visible_index: Optional[int] = None

        for index, item in enumerate(self.children):
            if not isinstance(item, ChatItem):
                continue
            
            item.display = filter_func(item.dialog.entity) and term in item.search_text
            
            if item.display and first_visible_index is None:
                first_visible_index = index

        # Ensure index always points to a visible item
        if first_visible_index is None:
            self.index = None
        elif self.index is None or not self.children[self.index].display:
            self.index = first_visible_index

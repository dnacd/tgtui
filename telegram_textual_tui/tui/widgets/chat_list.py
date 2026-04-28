"""
Widget for displaying the list of Telegram dialogs with filtering and smart navigation.
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

    def action_cursor_down(self) -> None:
        """Move cursor to the next visible item."""
        if self.index is None:
            return
            
        next_index = self.index + 1
        while next_index < len(self.children):
            if self.children[next_index].display:
                self.index = next_index
                return
            next_index += 1

    def action_cursor_up(self) -> None:
        """Move cursor to the previous visible item."""
        if self.index is None:
            return
            
        prev_index = self.index - 1
        while prev_index >= 0:
            if self.children[prev_index].display:
                self.index = prev_index
                return
            prev_index -= 1

    def apply_filter(self, category: str, search_term: str) -> None:
        """
        Filter the list items based on the active category and search term.
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

        if first_visible_index is None:
            self.index = None
        else:
            if self.index is None or self.index >= len(self.children) or not self.children[self.index].display:
                self.index = first_visible_index
            
            if self.index is not None:
                self.scroll_to_item(self.children[self.index])

        self.refresh(layout=True)

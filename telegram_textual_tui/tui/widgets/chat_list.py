"""
Widget for displaying the list of Telegram dialogs with avatars and filtering.

This module contains the ChatItem and ChatList widgets. ChatItem renders a single 
dialog entry with a stylized ANSI avatar miniature, while ChatList manages 
the collection of items, providing filtering by category and search term.
"""

import asyncio
import random
from typing import Any, Callable, Dict, Optional

from telethon.tl.types import Channel, Chat, User
from textual import message
from textual.app import ComposeResult
from textual.widgets import Label, ListItem, ListView

from telegram_textual_tui.utils.formatters import get_telegram_entity_title
from telegram_textual_tui.tui.widgets.ansi_image import AnsiImage


class ChatItem(ListItem):
    """
    An individual interactive item in the sidebar representing a Telegram chat.
    
    This widget lazily loads the chat partner's avatar or generates a unique 
    ANSI identicon if no profile photo is available.
    """

    def __init__(self, dialog: Any) -> None:
        """
        Initialize a chat list item.

        Args:
            dialog: A Telethon Dialog object containing chat and message metadata.
        """
        super().__init__()
        self.dialog = dialog
        self.title_text = get_telegram_entity_title(self.dialog.entity)
        self.search_text = self.title_text.lower()
        
        # Determine initials for the fallback state before the avatar is rendered
        first_char = self.title_text[0] if self.title_text else "?"
        self.initials = first_char.upper()

    def compose(self) -> ComposeResult:
        """
        Create the visual structure for the chat item using a horizontal layout.
        """
        yield AnsiImage(id="chat-avatar", image_data=None, fallback_text=self.initials, classes="chat-avatar-mini")
        yield Label(self.title_text, classes="chat-title", markup=False)
        if self.dialog.unread_count > 0:
            yield Label(str(self.dialog.unread_count), classes="chat-unread")

    def on_mount(self) -> None:
        """
        Check memory cache first to avoid background noise, otherwise spawn a worker.
        """
        try:
            telegram_manager = getattr(self.app, "telegram_manager", None)
            if telegram_manager:
                peer_id = self.dialog.entity.id
                cache_key = f"{peer_id}_small"
                if cache_key in telegram_manager.avatar_manager._memory_cache:
                    ansi_data = telegram_manager.avatar_manager._memory_cache[cache_key]
                    self.query_one("#chat-avatar", AnsiImage).update_image(ansi_data)
                    return
        except Exception:
            pass

        self.run_worker(self._load_avatar())

    async def _load_avatar(self) -> None:
        """
        Fetch and apply the ANSI avatar art asynchronously.
        
        This worker method interacts with the AvatarManager to retrieve either 
        a rendered photo or a generated identicon. It preserves disk storage 
        while leveraging memory caching for UI fluidity.
        """
        try:
            # Stagger loading slightly during initial batch rendering
            await asyncio.sleep(random.uniform(0.01, 0.1))
            
            telegram_manager = getattr(self.app, "telegram_manager", None)
            if not telegram_manager:
                return

            avatar_manager = telegram_manager.avatar_manager
            avatar_data = await avatar_manager.get_avatar(self.dialog.entity, size="small")
            
            avatar_widget = self.query_one("#chat-avatar", AnsiImage)
            if avatar_data:
                avatar_widget.update_image(avatar_data)
            else:
                avatar_widget.set_loading(False)
        except Exception:
            try:
                self.query_one("#chat-avatar", AnsiImage).set_loading(False)
            except Exception:
                pass


class ChatList(ListView):
    """
    A scrollable list of ChatItems with filtering capabilities.
    """

    class ReachedBottom(message.Message):
        """Sent when the list is scrolled near the bottom."""
        pass

    # Mapping of filter keys to predicate functions for easy classification
    FILTER_MAP: Dict[str, Callable[[Any], bool]] = {
        "all": lambda _: True,
        "private": lambda entity: isinstance(entity, User) and not entity.bot,
        "groups": lambda entity: isinstance(entity, (Chat, Channel)),
        "bots": lambda entity: isinstance(entity, User) and entity.bot,
    }

    def watch_scroll_offset(self) -> None:
        """Monitor scroll position and notify when near the bottom."""
        self._check_scroll_bottom()

    def on_mount(self) -> None:
        """Set up a periodic check for the scroll position to ensure reliability."""
        self.set_interval(0.3, self._check_scroll_bottom)

    def _check_scroll_bottom(self) -> None:
        """Check if the list is scrolled near the bottom and trigger pagination."""
        if self.virtual_size.height > 0:
            # If we are within half a screen height of the bottom
            if self.scroll_offset.y + self.size.height >= self.virtual_size.height - 5:
                self.post_message(self.ReachedBottom())

    def action_cursor_down(self) -> None:
        """
        Navigate the selection cursor to the next visible item.
        """
        if self.index is None:
            return
            
        next_index = self.index + 1
        while next_index < len(self.children):
            if self.children[next_index].display:
                self.index = next_index
                return
            next_index += 1

    def action_cursor_up(self) -> None:
        """
        Navigate the selection cursor to the previous visible item.
        """
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
        Filter the displayed chat items by category and search keyword.

        Args:
            category: One of 'all', 'private', 'groups', or 'bots'.
            search_term: The case-insensitive substring to search for in titles.
        """
        filter_func = self.FILTER_MAP.get(category, lambda _: True)
        term = search_term.lower()
        
        first_visible: Optional[int] = None

        for index, item in enumerate(self.children):
            if not isinstance(item, ChatItem):
                continue
            
            is_visible = filter_func(item.dialog.entity) and term in item.search_text
            item.display = is_visible
            
            if is_visible and first_visible is None:
                first_visible = index

        if first_visible is None:
            self.index = None
        else:
            # Maintain relative cursor position if the current item is still visible
            current_visible = (self.index is not None and 
                              self.index < len(self.children) and 
                              self.children[self.index].display)
            if not current_visible:
                self.index = first_visible
            
            if self.index is not None:
                self.scroll_to_item(self.children[self.index])

        self.refresh(layout=True)

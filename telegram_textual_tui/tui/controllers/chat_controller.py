"""
Controller for managing chat-level state, metadata, and dialog list.
"""

from typing import Any, List

from telethon import utils
from telegram_textual_tui.core.client import TelegramManager


class ChatController:
    """
    Handles chat-related metadata, status operations, and dialog list management.
    """

    def __init__(self, telegram_manager: TelegramManager) -> None:
        """
        Initialize the chat controller with a Telegram manager.
        """
        self._manager = telegram_manager

    async def get_read_outbox_max_id(self, entity: Any) -> int:
        """
        Fetch the ID of the last message read by the recipient in this chat.
        """
        try:
            target_id = utils.get_peer_id(entity)
            if not target_id:
                return 0
                
            dialogs = await self._manager.client.get_dialogs(limit=100)
            for d in dialogs:
                if utils.get_peer_id(d.entity) == target_id:
                    return getattr(d, "read_outbox_max_id", 0) or getattr(d.dialog, "read_outbox_max_id", 0)
        except (Exception, AttributeError):
            pass
        return 0

    async def mark_as_read(self, entity: Any) -> None:
        """
        Send a read acknowledgment for the given entity.
        """
        try:
            await self._manager.client.send_read_acknowledge(entity)
        except Exception:
            pass

    async def fetch_dialogs(self, limit: int = 20, offset_date: Any = None) -> List[Any]:
        """
        Fetch a slice of dialogs (chats) from Telegram.
        """
        return await self._manager.client.get_dialogs(limit=limit, offset_date=offset_date)

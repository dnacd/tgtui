"""
Controller for managing chat-level state, metadata, and dialog list.
"""

from typing import Any, List

from telegram_textual_tui.core.client import TelegramManager


class ChatController:
    """
    Handles chat-related metadata, status operations, and dialog list management.
    """

    def __init__(self, telegram_manager: TelegramManager) -> None:
        """
        Initialize the controller.
        """
        self._manager = telegram_manager

    async def get_read_outbox_max_id(self, entity: Any) -> int:
        """
        Fetch the ID of the last message read by the recipient in this chat.
        """
        try:
            from telethon import utils
            target_id = utils.get_peer_id(entity)
            if not target_id:
                return 0
                
            # Use get_dialogs which is often cached or more efficient than iter_dialogs for this
            dialogs = await self._manager.client.get_dialogs(limit=100)
            for d in dialogs:
                if utils.get_peer_id(d.entity) == target_id:
                    # Check both the custom dialog wrapper and the raw dialog object
                    val = getattr(d, "read_outbox_max_id", 0)
                    if not val and hasattr(d, "dialog"):
                        val = getattr(d.dialog, "read_outbox_max_id", 0)
                    return val
        except Exception:
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

    async def fetch_dialogs(self, limit: int = 100) -> List[Any]:
        """
        Fetch the list of dialogs (chats) from Telegram.
        """
        return await self._manager.client.get_dialogs(limit=limit)

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
            target_id = getattr(entity, "id", None)
            if not target_id:
                return 0
                
            async for dialog in self._manager.client.iter_dialogs(limit=100):
                if dialog.entity and dialog.entity.id == target_id:
                    return max(
                        getattr(dialog, "read_outbox_max_id", 0),
                        getattr(dialog.dialog, "read_outbox_max_id", 0) if hasattr(dialog, "dialog") else 0
                    )
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

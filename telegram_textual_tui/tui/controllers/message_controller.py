"""
Controller handling message-related business logic and permissions.
"""

from typing import Any, List, Tuple

from telethon.tl.types import Channel

from telegram_textual_tui.core.client import TelegramManager


class MessageController:
    """
    Manages message history loading, sending, and permission checks.
    """

    def __init__(self, telegram_manager: TelegramManager) -> None:
        """
        Initialize the controller with a Telegram manager.
        """
        self._manager = telegram_manager

    def get_messaging_status(self, entity: Any) -> Tuple[bool, str]:
        """
        Determine if messages can be sent to the given entity.

        Returns:
            A tuple of (can_send: bool, placeholder: str).
        """
        if isinstance(entity, Channel) and entity.broadcast:
            if not (entity.creator or entity.admin_rights):
                return False, "Read-only channel"
        
        return True, "Type a message..."

    async def fetch_history(self, entity: Any, limit: int = 20) -> List[Any]:
        """
        Load message history for a specific peer.
        """
        messages = []
        async for msg in self._manager.client.iter_messages(entity, limit=limit):
            messages.append(msg)
        return messages

    async def send_text(self, entity: Any, text: str) -> None:
        """
        Send a plain text message to the target entity.
        """
        await self._manager.client.send_message(entity=entity, message=text)

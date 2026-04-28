"""
Controller for managing message history fetching and pagination.
"""

from typing import Any, List

from telegram_textual_tui.core.client import TelegramManager


class HistoryController:
    """
    Handles optimized loading of message history from Telegram.
    """

    def __init__(self, telegram_manager: TelegramManager) -> None:
        """
        Initialize the history controller.
        """
        self._manager = telegram_manager

    async def get_messages(
        self, 
        entity: Any, 
        limit: int = 20, 
        offset_id: int = 0
    ) -> List[Any]:
        """
        Fetch a slice of message history.

        Args:
            entity: The peer to fetch history for.
            limit: Number of messages to fetch.
            offset_id: ID of the message to start fetching from (backwards).

        Returns:
            A list of Telethon Message objects.
        """
        messages = []
        async for msg in self._manager.client.iter_messages(
            entity, 
            limit=limit, 
            offset_id=offset_id
        ):
            messages.append(msg)
        return messages

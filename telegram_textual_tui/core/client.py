"""
Telegram client wrapper using Telethon.
"""

from telethon import TelegramClient
from telegram_textual_tui.core.config import Config, TELEGRAM_SESSION_PATH


class TelegramManager:
    """
    Manages the Telegram client lifecycle and session authentication state.
    """

    def __init__(self, config: Config):
        """
        Initialize the Telegram client with the provided configuration.

        Args:
            config: An object containing the Telegram API ID and Hash.
        """
        self.config = config
        self.client = TelegramClient(
            str(TELEGRAM_SESSION_PATH),
            config.api_id,
            config.api_hash,
        )

    async def connect_to_telegram(self) -> None:
        """
        Establish a connection to the Telegram servers.
        """
        await self.client.connect()

    async def disconnect_from_telegram(self) -> None:
        """
        Gracefully disconnect from the Telegram servers.
        """
        await self.client.disconnect()

    async def is_client_authorized(self) -> bool:
        """
        Verify if the current local session is authorized by the user.

        Returns:
            True if the session is authenticated, False otherwise.
        """
        return await self.client.is_user_authorized()

    async def get_authenticated_user_details(self):
        """
        Retrieve details of the currently authenticated Telegram user.

        Returns:
            A Telethon User object representing the authenticated user.
        """
        return await self.client.get_me()

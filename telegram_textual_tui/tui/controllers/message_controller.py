"""
Controller handling message-related business logic, permissions, and reactions.
"""

from typing import Any, List, Optional, Tuple

from telethon.tl.functions.messages import (
    GetAvailableReactionsRequest,
    GetMessageReactionsListRequest,
    GetRecentReactionsRequest,
    SendReactionRequest,
)
from telethon.tl.types import Channel, ReactionEmoji

from telegram_textual_tui.core.client import TelegramManager


class MessageController:
    """
    Manages message sending, permission checks, and reactions.
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

    async def send_text(self, entity: Any, text: str) -> None:
        """
        Send a plain text message to the target entity.
        """
        await self._manager.client.send_message(entity=entity, message=text)

    async def send_reaction(self, entity: Any, message_id: int, emoticon: str) -> None:
        """
        Send a reaction emoji to a specific message.
        """
        await self._manager.client(
            SendReactionRequest(
                peer=entity,
                msg_id=int(message_id),
                reaction=[ReactionEmoji(emoticon=emoticon)],
            )
        )

    async def get_message_reactions_users(self, entity: Any, message_id: int) -> List[Any]:
        """
        Fetch the list of users who reacted to a message.
        """
        reactions = await self._manager.client(
            GetMessageReactionsListRequest(peer=entity, id=int(message_id), limit=100)
        )
        return reactions.users

    async def get_available_reactions(self) -> List[str]:
        """
        Fetch available reaction emojis for the current account.
        """
        try:
            available = await self._manager.client(GetAvailableReactionsRequest(hash=0))
            if hasattr(available, "reactions"):
                return [
                    r.reaction.emoticon for r in available.reactions 
                    if isinstance(r.reaction, ReactionEmoji)
                ]
        except Exception:
            pass
        return []

    async def get_recent_reactions(self) -> List[str]:
        """
        Fetch recently used reaction emojis.
        """
        try:
            recent = await self._manager.client(GetRecentReactionsRequest(hash=0, limit=20))
            if hasattr(recent, "reactions"):
                return [r.emoticon for r in recent.reactions if isinstance(r, ReactionEmoji)]
        except Exception:
            pass
        return []

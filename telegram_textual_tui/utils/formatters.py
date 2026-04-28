"""
Utility formatters and helpers for Telegram entities and messages.
"""

from typing import Any, Optional
from telethon import utils
from telethon.tl.types import MessageReactions, ReactionEmoji


def get_telegram_entity_title(telegram_entity: Any) -> str:
    """
    Generate a human-readable title for a Telegram entity (User, Chat, or Channel).

    Args:
        telegram_entity: The Telegram object (User, Chat, Channel) to extract a title from.

    Returns:
        A string representing the most appropriate display name for the entity.
        Prioritizes: title -> first_name + last_name -> username -> ID.
    """
    if not telegram_entity:
        return "Unknown"

    entity_title = (
        getattr(telegram_entity, "title", None)
        or getattr(telegram_entity, "first_name", None)
        or getattr(telegram_entity, "username", None)
        or str(getattr(telegram_entity, "id", "Unknown"))
    )
    
    last_name = getattr(telegram_entity, "last_name", None)
    if last_name and not getattr(telegram_entity, "title", None):
        entity_title = f"{entity_title} {last_name}"
        
    return entity_title


def get_message_sender_id(message: Any) -> Optional[int]:
    """
    Extract the sender ID from a Telethon message object.

    Args:
        message: The Telethon message object.

    Returns:
        The integer peer ID of the sender, or None if it cannot be determined.
    """
    sender_id = getattr(message, "sender_id", None)
    if sender_id is not None:
        return sender_id

    from_id = getattr(message, "from_id", None)
    if from_id is not None:
        try:
            return utils.get_peer_id(from_id)
        except (Exception, ValueError):
            pass
    
    return None


def format_message_reactions(message_id: int, data: Optional[MessageReactions]) -> str:
    """
    Generate a clickable Rich markup string for message reactions.

    Args:
        message_id: The ID of the message the reactions belong to.
        data: The MessageReactions object from Telethon.

    Returns:
        A string containing Rich markup for displaying reactions and interaction links.
    """
    if not data or not data.results:
        return f" [@click=screen.send_reaction({message_id})][dim][React][/dim][/@click]"

    parts = []
    for result in data.results:
        char = result.reaction.emoticon if isinstance(result.reaction, ReactionEmoji) else "C"
        parts.append(f"{char}{result.count}")

    reaction_list = " ".join(parts)
    return (
        f" [@click=screen.show_reactions({message_id})][dim][{reaction_list}][/dim][/@click] "
        f"[@click=screen.send_reaction({message_id})][dim][+][/dim][/@click]"
    )

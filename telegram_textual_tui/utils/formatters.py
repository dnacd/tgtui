"""
Utility formatters for Telegram entities and messages.
"""

from typing import Any


def get_telegram_entity_title(telegram_entity: Any) -> str:
    """
    Generate a human-readable title for a Telegram entity (User, Chat, or Channel).

    Args:
        telegram_entity: The Telegram object to extract a title from.

    Returns:
        A string representing the most appropriate name for the entity.
    """
    entity_title = (
        getattr(telegram_entity, "title", None)
        or getattr(telegram_entity, "first_name", None)
        or getattr(telegram_entity, "username", None)
        or str(getattr(telegram_entity, "id", "Unknown"))
    )
    
    last_name_attribute = getattr(telegram_entity, "last_name", None)
    if last_name_attribute and not getattr(telegram_entity, "title", None):
        entity_title = f"{entity_title} {last_name_attribute}"
        
    return entity_title

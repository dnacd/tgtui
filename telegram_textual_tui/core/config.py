"""
Configuration management for the Telegram Textual TUI application.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


APPLICATION_DIRECTORY = Path.home() / ".telegram_textual_tui"
AVATAR_CACHE_DIRECTORY = APPLICATION_DIRECTORY / "avatars"
CONFIGURATION_FILE_PATH = APPLICATION_DIRECTORY / "config.json"
DEFAULT_SESSION_NAME = os.getenv("TG_SESSION", "telegram_textual_tui")
TELEGRAM_SESSION_PATH = APPLICATION_DIRECTORY / DEFAULT_SESSION_NAME


@dataclass
class Config:
    """
    Application configuration containing Telegram API credentials.
    
    Attributes:
        api_id: The Telegram API ID.
        api_hash: The Telegram API hash.
    """
    api_id: int
    api_hash: str


def ensure_application_directory_exists() -> None:
    """
    Ensure the application data directory exists on the local file system.
    """
    APPLICATION_DIRECTORY.mkdir(parents=True, exist_ok=True)


def load_configuration_from_environment() -> Optional[Config]:
    """
    Attempt to load the Telegram API configuration from environment variables.
    
    Returns:
        A Config instance if both API ID and API Hash are set, None otherwise.
    """
    api_id = os.getenv("TG_API_ID", "").strip()
    api_hash = os.getenv("TG_API_HASH", "").strip()

    if not api_id or not api_hash:
        return None

    try:
        return Config(api_id=int(api_id), api_hash=api_hash)
    except ValueError:
        return None


def load_configuration_from_file() -> Optional[Config]:
    """
    Attempt to load the Telegram API configuration from the local JSON file.
    
    Returns:
        A Config instance if the file exists and contains valid data, None otherwise.
    """
    if not CONFIGURATION_FILE_PATH.exists():
        return None

    try:
        raw_data = json.loads(CONFIGURATION_FILE_PATH.read_text(encoding="utf-8"))
        return Config(api_id=int(raw_data["api_id"]), api_hash=str(raw_data["api_hash"]))
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def load_application_configuration() -> Optional[Config]:
    """
    Load the application configuration by checking environment variables first, then the local file.
    
    Returns:
        A valid Config instance if found, None otherwise.
    """
    return load_configuration_from_environment() or load_configuration_from_file()


def save_application_configuration(config: Config) -> None:
    """
    Persist the provided configuration to the local JSON file.
    
    Args:
        config: The configuration object containing API credentials.
    """
    ensure_application_directory_exists()
    CONFIGURATION_FILE_PATH.write_text(
        json.dumps(
            {
                "api_id": config.api_id,
                "api_hash": config.api_hash,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

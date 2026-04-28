"""
Custom exceptions for the Telegram Textual TUI application.
"""

class TGTError(Exception):
    """Base exception for all TGT-related errors."""
    pass

class ConfigError(TGTError):
    """Raised when there is an issue with the configuration."""
    pass

class SessionError(TGTError):
    """Raised when there is an issue with the Telegram session."""
    pass

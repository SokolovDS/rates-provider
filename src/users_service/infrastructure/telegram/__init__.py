"""Telegram-specific infrastructure adapters for Users Service."""

from .ensure_user import EnsureTelegramUserMiddleware

__all__ = ["EnsureTelegramUserMiddleware"]

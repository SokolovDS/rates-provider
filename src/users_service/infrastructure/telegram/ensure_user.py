"""Middleware that guarantees user bootstrap for each Telegram update."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update, User

from users_service.application.resolve_or_create_telegram_user import (
    ResolveOrCreateTelegramUserCommand,
)
from users_service.domain.user import User as InternalUser


class _TelegramUserResolver(Protocol):
    """Protocol for user resolver use case consumed by middleware."""

    async def execute(self, command: ResolveOrCreateTelegramUserCommand) -> InternalUser:
        """Resolve or create a user for the incoming Telegram identity."""


class EnsureTelegramUserMiddleware(BaseMiddleware):
    """Resolve or create internal user account for supported Telegram events."""

    def __init__(self, use_case: _TelegramUserResolver) -> None:
        """Initialize middleware with user bootstrap use case."""
        self._use_case = use_case

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Ensure user exists for incoming message or callback query updates."""
        telegram_user = self._extract_user(event)
        if telegram_user is not None:
            current_user = await self._use_case.execute(
                ResolveOrCreateTelegramUserCommand(
                    telegram_user_id=telegram_user.id,
                    username=telegram_user.username,
                )
            )
            data["current_user"] = current_user

        return await handler(event, data)

    def _extract_user(self, event: TelegramObject) -> User | None:
        """Extract Telegram user from supported update payloads."""
        if isinstance(event, Update):
            message = event.message
            if isinstance(message, Message):
                return message.from_user

            callback_query = event.callback_query
            if isinstance(callback_query, CallbackQuery):
                return callback_query.from_user

        return None

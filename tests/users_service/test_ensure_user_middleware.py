"""Tests for Telegram middleware that ensures user bootstrap."""

import asyncio
from typing import Any

from aiogram.types import TelegramObject, Update

from users_service.application.resolve_or_create_telegram_user import (
    ResolveOrCreateTelegramUserCommand,
)
from users_service.domain.user import User, UserId, UserStatus
from users_service.infrastructure.telegram.ensure_user import (
    EnsureTelegramUserMiddleware,
)


class _RecordingUseCase:
    """Test double recording middleware calls."""

    def __init__(self) -> None:
        """Initialize call recorder state."""
        self.commands: list[ResolveOrCreateTelegramUserCommand] = []

    async def execute(self, command: ResolveOrCreateTelegramUserCommand) -> User:
        """Record command and return deterministic user payload."""
        self.commands.append(command)
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC)
        return User(
            user_id=UserId("00000000-0000-0000-0000-000000000001"),
            status=UserStatus.ACTIVE,
            created_at=timestamp,
            updated_at=timestamp,
            last_seen_at=timestamp,
        )


def _message_update() -> Update:
    """Build minimal message update payload."""
    return Update.model_validate(
        {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "date": 1710000000,
                "chat": {"id": 1001, "type": "private"},
                "from": {
                    "id": 1001,
                    "is_bot": False,
                    "first_name": "User",
                    "username": "tester",
                },
                "text": "/start",
            },
        }
    )


def _callback_update() -> Update:
    """Build minimal callback query update payload."""
    return Update.model_validate(
        {
            "update_id": 2,
            "callback_query": {
                "id": "cb-1",
                "from": {
                    "id": 1002,
                    "is_bot": False,
                    "first_name": "Other",
                    "username": "tester2",
                },
                "chat_instance": "ci-1",
                "data": "rates_menu",
            },
        }
    )


async def _handler(_: TelegramObject, data: dict[str, Any]) -> dict[str, Any]:
    """Echo contextual data for middleware assertions."""
    return data


def test_ensure_user_middleware_bootstraps_user_for_message_update() -> None:
    """Middleware should call user bootstrap use case for message updates."""
    use_case = _RecordingUseCase()
    middleware = EnsureTelegramUserMiddleware(use_case)

    data = asyncio.run(middleware(_handler, _message_update(), {}))

    assert len(use_case.commands) == 1
    assert use_case.commands[0].telegram_user_id == 1001
    assert use_case.commands[0].username == "tester"
    assert "current_user" in data


def test_ensure_user_middleware_bootstraps_user_for_callback_update() -> None:
    """Middleware should call user bootstrap use case for callback updates."""
    use_case = _RecordingUseCase()
    middleware = EnsureTelegramUserMiddleware(use_case)

    data = asyncio.run(middleware(_handler, _callback_update(), {}))

    assert len(use_case.commands) == 1
    assert use_case.commands[0].telegram_user_id == 1002
    assert use_case.commands[0].username == "tester2"
    assert "current_user" in data


def test_ensure_user_middleware_skips_updates_without_supported_user_source() -> None:
    """Middleware should not fail when update has no message/callback user."""
    use_case = _RecordingUseCase()
    middleware = EnsureTelegramUserMiddleware(use_case)

    update = Update.model_validate({"update_id": 3})
    data = asyncio.run(middleware(_handler, update, {}))

    assert use_case.commands == []
    assert "current_user" not in data

"""Tests for Telegram user bootstrap use case."""

import asyncio

from users_service.application.resolve_or_create_telegram_user import (
    ResolveOrCreateTelegramUserCommand,
    ResolveOrCreateTelegramUserUseCase,
)
from users_service.infrastructure.memory_user_repository import InMemoryUserRepository


def test_resolve_or_create_returns_same_user_for_same_telegram_id() -> None:
    """Use case should be idempotent for repeated Telegram identity requests."""
    repository = InMemoryUserRepository()
    use_case = ResolveOrCreateTelegramUserUseCase(repository)

    first_user = asyncio.run(
        use_case.execute(
            ResolveOrCreateTelegramUserCommand(
                telegram_user_id=1001,
                username="tester",
            )
        )
    )
    second_user = asyncio.run(
        use_case.execute(
            ResolveOrCreateTelegramUserCommand(
                telegram_user_id=1001,
                username="tester",
            )
        )
    )

    assert first_user.user_id == second_user.user_id


def test_resolve_or_create_returns_distinct_users_for_distinct_telegram_ids() -> None:
    """Use case should create separate users for distinct Telegram identities."""
    repository = InMemoryUserRepository()
    use_case = ResolveOrCreateTelegramUserUseCase(repository)

    first_user = asyncio.run(
        use_case.execute(
            ResolveOrCreateTelegramUserCommand(telegram_user_id=1001))
    )
    second_user = asyncio.run(
        use_case.execute(
            ResolveOrCreateTelegramUserCommand(telegram_user_id=1002))
    )

    assert first_user.user_id != second_user.user_id

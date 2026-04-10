"""Tests for in-memory user repository."""

import asyncio

from modules.identity.domain.user import ExternalIdentity, ExternalIdentityProvider
from modules.identity.infrastructure.memory_user_repository import InMemoryUserRepository


def test_memory_user_repository_get_or_create_is_idempotent() -> None:
    """Repeated get-or-create calls should return the same internal user."""
    repository = InMemoryUserRepository()
    identity = ExternalIdentity(
        provider=ExternalIdentityProvider.TELEGRAM,
        subject="1001",
        username="tester",
    )

    first_user = asyncio.run(
        repository.get_or_create_by_external_identity(identity))
    second_user = asyncio.run(
        repository.get_or_create_by_external_identity(identity))

    assert first_user.user_id == second_user.user_id


def test_memory_user_repository_creates_distinct_users_for_distinct_subjects() -> None:
    """Different external subjects should map to different internal users."""
    repository = InMemoryUserRepository()
    first_identity = ExternalIdentity(
        provider=ExternalIdentityProvider.TELEGRAM,
        subject="1001",
    )
    second_identity = ExternalIdentity(
        provider=ExternalIdentityProvider.TELEGRAM,
        subject="1002",
    )

    first_user = asyncio.run(
        repository.get_or_create_by_external_identity(first_identity))
    second_user = asyncio.run(
        repository.get_or_create_by_external_identity(second_identity))

    assert first_user.user_id != second_user.user_id

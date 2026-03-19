"""Tests for SQLite user repository."""

import asyncio
import sqlite3
from pathlib import Path

import pytest

from users_service.domain.user import ExternalIdentity, ExternalIdentityProvider
from users_service.infrastructure.sqlite_user_repository import SQLiteUserRepository


def test_sqlite_user_repository_get_or_create_is_idempotent(tmp_path: Path) -> None:
    """Repeated get-or-create calls should reuse existing user mapping."""
    database_path = tmp_path / "users.sqlite3"
    repository = SQLiteUserRepository(str(database_path))
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


def test_sqlite_user_repository_persists_user_mapping_between_instances(
    tmp_path: Path,
) -> None:
    """Identity mapping should survive repository re-instantiation."""
    database_path = tmp_path / "users.sqlite3"
    first_repository = SQLiteUserRepository(str(database_path))
    identity = ExternalIdentity(
        provider=ExternalIdentityProvider.TELEGRAM,
        subject="1001",
    )

    first_user = asyncio.run(
        first_repository.get_or_create_by_external_identity(identity))

    second_repository = SQLiteUserRepository(str(database_path))
    second_user = asyncio.run(
        second_repository.get_or_create_by_external_identity(identity))

    assert first_user.user_id == second_user.user_id


def test_sqlite_user_repository_enforces_foreign_keys(tmp_path: Path) -> None:
    """Repository connection should enforce foreign-key constraints in SQLite."""
    database_path = tmp_path / "users.sqlite3"
    repository = SQLiteUserRepository(str(database_path))

    with repository._connect() as connection:  # noqa: SLF001
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO user_external_identities (
                    user_id,
                    provider,
                    provider_subject,
                    provider_username,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "00000000-0000-0000-0000-000000000099",
                    "telegram",
                    "subject-1",
                    None,
                    "2026-03-19T00:00:00+00:00",
                    "2026-03-19T00:00:00+00:00",
                ),
            )

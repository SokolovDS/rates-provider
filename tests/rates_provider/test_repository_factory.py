"""Tests for runtime repository factory wiring."""

from pathlib import Path

import pytest

from rates_provider.infrastructure.memory_exchange_rate_repository import (
    InMemoryExchangeRateRepository,
)
from rates_provider.infrastructure.repository_factory import (
    build_exchange_rate_repository,
    build_user_repository,
)
from rates_provider.infrastructure.sqlite_exchange_rate_repository import (
    SQLiteExchangeRateRepository,
)
from users_service.infrastructure.memory_user_repository import InMemoryUserRepository
from users_service.infrastructure.sqlite_user_repository import SQLiteUserRepository


def test_build_repository_returns_memory_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Factory should return in-memory repository when configured explicitly."""
    monkeypatch.setenv("STORAGE_BACKEND", "memory")

    repository = build_exchange_rate_repository()

    assert isinstance(repository, InMemoryExchangeRateRepository)


def test_build_repository_returns_sqlite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Factory should return SQLite repository and create configured DB directory."""
    database_path = tmp_path / "db" / "rates.sqlite3"
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_RATES_DB_PATH", str(database_path))

    repository = build_exchange_rate_repository()

    assert isinstance(repository, SQLiteExchangeRateRepository)
    assert database_path.parent.exists()


def test_build_repository_raises_for_unknown_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory should surface config error for unsupported backend value."""
    monkeypatch.setenv("STORAGE_BACKEND", "unknown")

    with pytest.raises(RuntimeError, match="must be one of"):
        build_exchange_rate_repository()


def test_build_user_repository_returns_memory_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory should return in-memory user repository for memory backend."""
    monkeypatch.setenv("STORAGE_BACKEND", "memory")

    repository = build_user_repository()

    assert isinstance(repository, InMemoryUserRepository)


def test_build_user_repository_returns_sqlite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Factory should return SQLite user repository for sqlite backend."""
    database_path = tmp_path / "db" / "users.sqlite3"
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_USERS_DB_PATH", str(database_path))

    repository = build_user_repository()

    assert isinstance(repository, SQLiteUserRepository)

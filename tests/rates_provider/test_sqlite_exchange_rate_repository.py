"""Tests for the SQLite exchange-rate repository."""

import asyncio
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.infrastructure.sqlite_exchange_rate_repository import (
    SQLiteExchangeRateRepository,
)


def test_sqlite_repository_lists_active_latest_rates_in_pair_order(
    tmp_path: Path,
) -> None:
    """Repository should return one active latest record per pair."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))

    first_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )
    second_rate = ExchangeRate(
        source_currency=CurrencyCode("EUR"),
        target_currency=CurrencyCode("RUB"),
        rate_value=Decimal("100.10"),
    )

    asyncio.run(repository.add("user-1", first_rate))
    asyncio.run(repository.add("user-1", second_rate))

    assert list(asyncio.run(repository.list_all("user-1"))) == [
        second_rate,
        first_rate,
    ]


def test_sqlite_repository_persists_rates_between_instances(tmp_path: Path) -> None:
    """Repository should persist latest active rates between instances."""
    database_path = tmp_path / "rates.sqlite3"
    first_repository = SQLiteExchangeRateRepository(str(database_path))

    exchange_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )

    asyncio.run(first_repository.add("user-1", exchange_rate))

    second_repository = SQLiteExchangeRateRepository(str(database_path))
    loaded_rates = asyncio.run(second_repository.list_all("user-1"))

    assert list(loaded_rates) == [exchange_rate]


def test_sqlite_repository_add_overwrites_existing_pair_with_latest_rate(
    tmp_path: Path,
) -> None:
    """Repeated add for same pair should upsert latest value."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))

    first_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )
    second_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("91.10"),
    )

    asyncio.run(repository.add("user-1", first_rate))
    asyncio.run(repository.add("user-1", second_rate))

    assert list(asyncio.run(repository.list_all("user-1"))) == [second_rate]


def test_sqlite_repository_returns_only_rates_for_requested_user(
    tmp_path: Path,
) -> None:
    """SQLite repository should isolate exchange rates by user identifier."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))

    user_one_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )
    user_two_rate = ExchangeRate(
        source_currency=CurrencyCode("EUR"),
        target_currency=CurrencyCode("RUB"),
        rate_value=Decimal("100.10"),
    )

    asyncio.run(repository.add("user-1", user_one_rate))
    asyncio.run(repository.add("user-2", user_two_rate))

    assert list(asyncio.run(repository.list_all("user-1"))) == [user_one_rate]
    assert list(asyncio.run(repository.list_all("user-2"))) == [user_two_rate]


def test_sqlite_repository_update_changes_existing_active_pair(tmp_path: Path) -> None:
    """Update should modify existing active pair value in SQLite storage."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))

    initial_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )
    updated_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("95.25"),
    )

    asyncio.run(repository.add("user-1", initial_rate))
    asyncio.run(repository.update("user-1", updated_rate))

    assert list(asyncio.run(repository.list_all("user-1"))) == [updated_rate]


def test_sqlite_repository_update_raises_when_pair_missing(tmp_path: Path) -> None:
    """Update should fail when active pair does not exist in storage."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))
    updated_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("95.25"),
    )

    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(repository.update("user-1", updated_rate))


def test_sqlite_repository_soft_delete_hides_pair_from_active_list(tmp_path: Path) -> None:
    """Soft delete should hide pair from active list_all output."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))
    exchange_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )

    asyncio.run(repository.add("user-1", exchange_rate))
    asyncio.run(
        repository.delete(
            "user-1",
            CurrencyCode("USD"),
            CurrencyCode("EUR"),
        )
    )

    assert list(asyncio.run(repository.list_all("user-1"))) == []


def test_sqlite_repository_soft_delete_raises_when_pair_missing(tmp_path: Path) -> None:
    """Soft delete should fail when active pair does not exist."""
    database_path = tmp_path / "rates.sqlite3"
    repository = SQLiteExchangeRateRepository(str(database_path))

    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(
            repository.delete(
                "user-1",
                CurrencyCode("USD"),
                CurrencyCode("EUR"),
            )
        )


def test_sqlite_repository_migrates_history_to_latest_only(tmp_path: Path) -> None:
    """Repository should collapse historical duplicates to latest record on migration."""
    database_path = tmp_path / "rates.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            source_currency TEXT NOT NULL,
            target_currency TEXT NOT NULL,
            rate_value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO exchange_rates (
            user_id,
            source_currency,
            target_currency,
            rate_value,
            created_at
        )
        VALUES
            ('user-1', 'USD', 'EUR', '90.50', '2026-03-20T10:00:00+00:00'),
            ('user-1', 'USD', 'EUR', '91.10', '2026-03-20T11:00:00+00:00'),
            ('user-1', 'EUR', 'RUB', '100.10', '2026-03-20T12:00:00+00:00')
        """
    )
    connection.commit()
    connection.close()

    repository = SQLiteExchangeRateRepository(str(database_path))

    loaded_rates = list(asyncio.run(repository.list_all("user-1")))
    loaded_tuples = [
        (rate.source_currency.value, rate.target_currency.value, rate.rate_value)
        for rate in loaded_rates
    ]
    assert loaded_tuples == [
        ("EUR", "RUB", Decimal("100.10")),
        ("USD", "EUR", Decimal("91.10")),
    ]

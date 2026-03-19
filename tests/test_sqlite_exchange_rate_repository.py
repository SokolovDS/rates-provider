"""Tests for the SQLite exchange-rate repository."""

import asyncio
from decimal import Decimal
from pathlib import Path

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.infrastructure.sqlite_exchange_rate_repository import (
    SQLiteExchangeRateRepository,
)


def test_sqlite_repository_lists_all_rates_in_insertion_order(
    tmp_path: Path,
) -> None:
    """Repository should preserve insertion order for all stored exchange rates."""
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

    asyncio.run(repository.add(first_rate))
    asyncio.run(repository.add(second_rate))

    assert list(asyncio.run(repository.list_all())) == [
        first_rate,
        second_rate,
    ]


def test_sqlite_repository_persists_rates_between_instances(tmp_path: Path) -> None:
    """Repository should keep history in DB file across repository instances."""
    database_path = tmp_path / "rates.sqlite3"
    first_repository = SQLiteExchangeRateRepository(str(database_path))

    exchange_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )

    asyncio.run(first_repository.add(exchange_rate))

    second_repository = SQLiteExchangeRateRepository(str(database_path))
    loaded_rates = asyncio.run(second_repository.list_all())

    assert list(loaded_rates) == [exchange_rate]

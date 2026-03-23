"""Tests for the in-memory exchange-rate repository."""

import asyncio
from decimal import Decimal

import pytest

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.infrastructure.memory_exchange_rate_repository import (
    InMemoryExchangeRateRepository,
)


def test_repository_lists_active_latest_rates_in_pair_order() -> None:
    """Repository should return one active latest record per pair."""
    repository = InMemoryExchangeRateRepository()

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


def test_repository_add_overwrites_existing_pair_with_latest_rate() -> None:
    """Repository add should upsert latest value for duplicated pair."""
    repository = InMemoryExchangeRateRepository()

    old_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )
    new_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("91.10"),
    )

    asyncio.run(repository.add("user-1", old_rate))
    asyncio.run(repository.add("user-1", new_rate))

    assert list(asyncio.run(repository.list_all("user-1"))) == [new_rate]


def test_repository_returns_only_rates_for_requested_user() -> None:
    """Repository should isolate in-memory rates by user identifier."""
    repository = InMemoryExchangeRateRepository()

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


def test_repository_update_changes_existing_active_rate() -> None:
    """Update should replace value for an existing active pair."""
    repository = InMemoryExchangeRateRepository()

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


def test_repository_update_raises_when_pair_missing() -> None:
    """Update should fail when the pair is absent in active records."""
    repository = InMemoryExchangeRateRepository()
    updated_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("95.25"),
    )

    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(repository.update("user-1", updated_rate))


def test_repository_soft_delete_hides_rate_from_active_list() -> None:
    """Soft delete should hide pair from list_all results."""
    repository = InMemoryExchangeRateRepository()
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


def test_repository_soft_delete_raises_when_pair_missing() -> None:
    """Soft delete should fail when pair is absent in active records."""
    repository = InMemoryExchangeRateRepository()

    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(
            repository.delete(
                "user-1",
                CurrencyCode("USD"),
                CurrencyCode("EUR"),
            )
        )

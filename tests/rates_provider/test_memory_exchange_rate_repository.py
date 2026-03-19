"""Tests for the in-memory exchange-rate repository."""

import asyncio
from decimal import Decimal

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.infrastructure.memory_exchange_rate_repository import (
    InMemoryExchangeRateRepository,
)


def test_repository_lists_all_rates_in_insertion_order() -> None:
    """Repository should preserve insertion order for all stored exchange rates."""
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
        first_rate, second_rate]


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

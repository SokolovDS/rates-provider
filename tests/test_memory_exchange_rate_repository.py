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

    asyncio.run(repository.add(first_rate))
    asyncio.run(repository.add(second_rate))

    assert list(asyncio.run(repository.list_all())) == [
        first_rate, second_rate]

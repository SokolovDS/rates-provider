"""Tests for the in-memory market rates reader."""

import asyncio
from decimal import Decimal

from modules.market_rates.infrastructure.in_memory_market_rates_reader import (
    InMemoryMarketRatesReader,
)


def test_in_memory_market_rates_reader_returns_non_empty_list() -> None:
    """Reader should return at least one rate entry."""
    reader = InMemoryMarketRatesReader()
    rates = asyncio.run(reader.list_rates())
    assert len(rates) > 0


def test_in_memory_market_rates_reader_contains_usd_eur_pair() -> None:
    """Reader should include the USD/EUR pair."""
    reader = InMemoryMarketRatesReader()
    rates = asyncio.run(reader.list_rates())
    pairs = {(r.source_currency, r.target_currency) for r in rates}
    assert ("USD", "EUR") in pairs


def test_in_memory_market_rates_reader_all_rate_values_positive() -> None:
    """All market rate values must be strictly positive."""
    reader = InMemoryMarketRatesReader()
    rates = asyncio.run(reader.list_rates())
    assert all(r.rate_value > Decimal("0") for r in rates)


def test_in_memory_market_rates_reader_all_currency_codes_three_letters() -> None:
    """All currency codes in market rates must be three uppercase ASCII letters."""
    reader = InMemoryMarketRatesReader()
    rates = asyncio.run(reader.list_rates())
    for entry in rates:
        assert len(entry.source_currency) == 3 and entry.source_currency.isalpha()
        assert len(entry.target_currency) == 3 and entry.target_currency.isalpha()


def test_in_memory_market_rates_reader_no_identical_pair() -> None:
    """No entry should have the same source and target currency."""
    reader = InMemoryMarketRatesReader()
    rates = asyncio.run(reader.list_rates())
    assert all(r.source_currency != r.target_currency for r in rates)

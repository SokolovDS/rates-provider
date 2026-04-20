"""Tests for the ListMarketRatesUseCase application use case."""

import asyncio
from collections.abc import Sequence
from decimal import Decimal

from modules.market_rates.application.list_market_rates import ListMarketRatesUseCase
from modules.market_rates.contracts.dtos import MarketRateEntry
from modules.market_rates.contracts.reader_port import MarketRatesReaderPort


class PreloadedMarketRatesReader(MarketRatesReaderPort):
    """Test double that returns a fixed list of market rate entries."""

    def __init__(self, rates: Sequence[MarketRateEntry] = ()) -> None:
        """Initialize with a pre-set list of rates."""
        self._rates = rates

    async def list_rates(self) -> Sequence[MarketRateEntry]:
        """Return the pre-loaded rates."""
        return self._rates


def _entry(source: str, target: str, value: str) -> MarketRateEntry:
    """Build a MarketRateEntry for test use."""
    return MarketRateEntry(
        source_currency=source,
        target_currency=target,
        rate_value=Decimal(value),
    )


def test_list_market_rates_returns_all_entries() -> None:
    """Use case result must contain every entry provided by the reader."""
    rates = [_entry("USD", "EUR", "0.92"), _entry("EUR", "USD", "1.08")]
    use_case = ListMarketRatesUseCase(PreloadedMarketRatesReader(rates))
    result = asyncio.run(use_case.execute())
    assert set(result.exchange_rates) == set(rates)


def test_list_market_rates_preserves_count() -> None:
    """Result entry count must match the number of rates from the reader."""
    rates = [
        _entry("USD", "RUB", "90.0"),
        _entry("EUR", "RUB", "98.0"),
        _entry("CNY", "RUB", "12.5"),
    ]
    use_case = ListMarketRatesUseCase(PreloadedMarketRatesReader(rates))
    result = asyncio.run(use_case.execute())
    assert len(result.exchange_rates) == 3


def test_list_market_rates_empty_reader_returns_empty() -> None:
    """Use case must return an empty tuple when the reader has no rates."""
    use_case = ListMarketRatesUseCase(PreloadedMarketRatesReader())
    result = asyncio.run(use_case.execute())
    assert result.exchange_rates == ()

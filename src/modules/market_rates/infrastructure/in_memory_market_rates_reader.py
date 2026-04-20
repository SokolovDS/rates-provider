"""In-memory market rates reader with hardcoded realistic exchange rates."""

from collections.abc import Sequence
from decimal import Decimal

from modules.market_rates.contracts.dtos import MarketRateEntry
from modules.market_rates.contracts.reader_port import MarketRatesReaderPort

_MARKET_RATES: tuple[MarketRateEntry, ...] = (
    # USD pairs
    MarketRateEntry("USD", "EUR", Decimal("0.92")),
    MarketRateEntry("EUR", "USD", Decimal("1.09")),
    MarketRateEntry("USD", "RUB", Decimal("90.00")),
    MarketRateEntry("RUB", "USD", Decimal("0.0111")),
    MarketRateEntry("USD", "CNY", Decimal("7.24")),
    MarketRateEntry("CNY", "USD", Decimal("0.138")),
    MarketRateEntry("USD", "THB", Decimal("35.10")),
    MarketRateEntry("THB", "USD", Decimal("0.0285")),
    # EUR pairs
    MarketRateEntry("EUR", "RUB", Decimal("98.00")),
    MarketRateEntry("RUB", "EUR", Decimal("0.0102")),
    MarketRateEntry("EUR", "CNY", Decimal("7.88")),
    MarketRateEntry("CNY", "EUR", Decimal("0.127")),
    MarketRateEntry("EUR", "THB", Decimal("38.20")),
    MarketRateEntry("THB", "EUR", Decimal("0.0262")),
    # CNY pairs
    MarketRateEntry("CNY", "RUB", Decimal("12.43")),
    MarketRateEntry("RUB", "CNY", Decimal("0.0805")),
    MarketRateEntry("CNY", "THB", Decimal("4.85")),
    MarketRateEntry("THB", "CNY", Decimal("0.206")),
    # RUB/THB
    MarketRateEntry("RUB", "THB", Decimal("0.390")),
    MarketRateEntry("THB", "RUB", Decimal("2.564")),
)


class InMemoryMarketRatesReader(MarketRatesReaderPort):
    """Market rates reader backed by a hardcoded in-memory dataset."""

    async def list_rates(self) -> Sequence[MarketRateEntry]:
        """Return the fixed set of market exchange-rate records."""
        return _MARKET_RATES

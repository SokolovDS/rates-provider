"""Public DTOs exported by the market_rates contracts layer."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MarketRateEntry:
    """Public DTO representing a single market-sourced exchange-rate record."""

    source_currency: str
    target_currency: str
    rate_value: Decimal

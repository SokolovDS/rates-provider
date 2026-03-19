"""In-memory exchange-rate repository implementation."""

from collections.abc import Sequence

from rates_provider.domain.exchange_rate import ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class InMemoryExchangeRateRepository(ExchangeRateRepository):
    """Append-only in-memory storage for exchange-rate history."""

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._exchange_rates: list[ExchangeRate] = []

    async def add(self, exchange_rate: ExchangeRate) -> None:
        """Append a new exchange-rate record to storage."""
        self._exchange_rates.append(exchange_rate)

    async def list_all(self) -> Sequence[ExchangeRate]:
        """Return all stored exchange-rate records in insertion order."""
        return tuple(self._exchange_rates)

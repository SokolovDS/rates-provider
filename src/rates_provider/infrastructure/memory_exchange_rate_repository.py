"""In-memory exchange-rate repository implementation."""

from collections.abc import Sequence

from rates_provider.domain.exchange_rate import ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class InMemoryExchangeRateRepository(ExchangeRateRepository):
    """Append-only in-memory storage for exchange-rate history."""

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._exchange_rates: list[tuple[str, ExchangeRate]] = []

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Append a new exchange-rate record to storage."""
        self._exchange_rates.append((user_id, exchange_rate))

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return all stored exchange-rate records for the requested user."""
        return tuple(
            exchange_rate
            for rate_user_id, exchange_rate in self._exchange_rates
            if rate_user_id == user_id
        )

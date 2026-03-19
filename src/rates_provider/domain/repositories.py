"""Repository ports for exchange-rate storage."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .exchange_rate import ExchangeRate


class ExchangeRateRepository(ABC):
    """Port describing append-only storage for exchange-rate history."""

    @abstractmethod
    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Store a single exchange-rate record."""

    @abstractmethod
    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return stored exchange-rate records for a specific user."""

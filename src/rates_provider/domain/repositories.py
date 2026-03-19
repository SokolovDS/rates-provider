"""Repository ports for exchange-rate storage."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .exchange_rate import ExchangeRate


class ExchangeRateRepository(ABC):
    """Port describing append-only storage for exchange-rate history."""

    @abstractmethod
    async def add(self, exchange_rate: ExchangeRate) -> None:
        """Store a single exchange-rate record."""

    @abstractmethod
    async def list_all(self) -> Sequence[ExchangeRate]:
        """Return all stored exchange-rate records in insertion order."""

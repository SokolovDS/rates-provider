"""Repository ports for user-rates storage."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .exchange_rate import CurrencyCode, ExchangeRate


class ExchangeRateRepository(ABC):
    """Port describing latest-only storage for user-scoped exchange rates."""

    @abstractmethod
    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Upsert a single active exchange-rate record for a currency pair."""

    @abstractmethod
    async def update(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Update an existing active exchange-rate record for a currency pair."""

    @abstractmethod
    async def delete(
        self,
        user_id: str,
        source_currency: CurrencyCode,
        target_currency: CurrencyCode,
    ) -> None:
        """Soft-delete an active exchange-rate record for a currency pair."""

    @abstractmethod
    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return all active latest exchange-rate records for a user."""

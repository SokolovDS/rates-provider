"""In-memory exchange-rate repository implementation."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


@dataclass(slots=True)
class _StoredExchangeRate:
    """Internal mutable record with soft-delete metadata."""

    exchange_rate: ExchangeRate
    deleted_at: datetime | None = None


class InMemoryExchangeRateRepository(ExchangeRateRepository):
    """Latest-only in-memory storage with soft deletion per currency pair."""

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._exchange_rates: dict[tuple[str,
                                         str, str], _StoredExchangeRate] = {}

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Upsert an active exchange-rate record for a user currency pair."""
        key = self._rate_key(user_id, exchange_rate)
        self._exchange_rates[key] = _StoredExchangeRate(
            exchange_rate=exchange_rate,
            deleted_at=None,
        )

    async def update(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Update an existing active exchange-rate record for a user pair."""
        key = self._rate_key(user_id, exchange_rate)
        stored_rate = self._exchange_rates.get(key)
        if stored_rate is None or stored_rate.deleted_at is not None:
            source = exchange_rate.source_currency.value
            target = exchange_rate.target_currency.value
            raise ValueError(
                f"Exchange rate {source}->{target} does not exist.")

        self._exchange_rates[key] = _StoredExchangeRate(
            exchange_rate=exchange_rate,
            deleted_at=None,
        )

    async def delete(
        self,
        user_id: str,
        source_currency: CurrencyCode,
        target_currency: CurrencyCode,
    ) -> None:
        """Soft-delete an active exchange-rate record for the provided pair."""
        key = self._pair_key(user_id, source_currency, target_currency)
        stored_rate = self._exchange_rates.get(key)
        if stored_rate is None or stored_rate.deleted_at is not None:
            raise ValueError(
                f"Exchange rate {source_currency.value}->{target_currency.value} does not exist."
            )

        stored_rate.deleted_at = datetime.now(tz=UTC)

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return active latest exchange-rate records for the requested user."""
        active_rates: list[ExchangeRate] = []
        for (rate_user_id, _, _), stored_rate in self._exchange_rates.items():
            if rate_user_id != user_id or stored_rate.deleted_at is not None:
                continue
            active_rates.append(stored_rate.exchange_rate)

        active_rates.sort(
            key=lambda exchange_rate: (
                exchange_rate.source_currency.value,
                exchange_rate.target_currency.value,
            )
        )
        return tuple(active_rates)

    @staticmethod
    def _rate_key(user_id: str, exchange_rate: ExchangeRate) -> tuple[str, str, str]:
        """Build dictionary key for a user-scoped exchange-rate entity."""
        return (
            user_id,
            exchange_rate.source_currency.value,
            exchange_rate.target_currency.value,
        )

    @staticmethod
    def _pair_key(
        user_id: str,
        source_currency: CurrencyCode,
        target_currency: CurrencyCode,
    ) -> tuple[str, str, str]:
        """Build dictionary key for user and currency pair values."""
        return (
            user_id,
            source_currency.value,
            target_currency.value,
        )

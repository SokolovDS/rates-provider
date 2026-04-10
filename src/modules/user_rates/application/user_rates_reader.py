"""Adapter that implements UserRatesReaderPort over ExchangeRateRepository."""

from collections.abc import Sequence

from app.shared._validation import normalize_user_id
from modules.user_rates.contracts.dtos import RateEntry
from modules.user_rates.contracts.reader_port import UserRatesReaderPort
from modules.user_rates.domain.repositories import ExchangeRateRepository


class UserRatesReader(UserRatesReaderPort):
    """Fetch user-scoped exchange rates from the domain repository."""

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize reader with an exchange-rate repository."""
        self._repository = repository

    async def list_rates(self, user_id: str) -> Sequence[RateEntry]:
        """Return active exchange-rate records mapped to public RateEntry DTOs."""
        normalized_user_id = normalize_user_id(user_id)
        exchange_rates = await self._repository.list_all(normalized_user_id)
        return tuple(
            RateEntry(
                source_currency=rate.source_currency.value,
                target_currency=rate.target_currency.value,
                rate_value=rate.rate_value,
                created_at=rate.created_at,
            )
            for rate in exchange_rates
        )

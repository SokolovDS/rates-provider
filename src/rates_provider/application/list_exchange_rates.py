"""Application use case for listing active latest exchange-rate records."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from rates_provider.application._validation import normalize_user_id
from rates_provider.domain.repositories import ExchangeRateRepository


@dataclass(frozen=True, slots=True)
class ExchangeRateListItem:
    """Output DTO describing a single active exchange-rate record."""

    source_currency: str
    target_currency: str
    rate_value: Decimal
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ListExchangeRatesResult:
    """Output DTO describing active latest exchange-rate records."""

    exchange_rates: tuple[ExchangeRateListItem, ...]


class ListExchangeRatesUseCase:
    """Read and return active latest exchange rates from storage."""

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize the use case with an exchange-rate repository."""
        self._repository = repository

    async def execute(self, user_id: str) -> ListExchangeRatesResult:
        """Load active latest exchange-rate records and map them to DTOs."""
        normalized_user_id = normalize_user_id(user_id)
        exchange_rates = await self._repository.list_all(normalized_user_id)
        return ListExchangeRatesResult(
            exchange_rates=tuple(
                ExchangeRateListItem(
                    source_currency=exchange_rate.source_currency.value,
                    target_currency=exchange_rate.target_currency.value,
                    rate_value=exchange_rate.rate_value,
                    created_at=exchange_rate.created_at,
                )
                for exchange_rate in exchange_rates
            )
        )

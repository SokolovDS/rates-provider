"""Application use case for updating active exchange-rate records."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from rates_provider.application._validation import normalize_user_id
from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


@dataclass(frozen=True, slots=True)
class UpdateExchangeRateCommand:
    """Input data required to update an existing exchange-rate record."""

    user_id: str
    source_currency: str
    target_currency: str
    rate_value: Decimal
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UpdateExchangeRateResult:
    """Output data returned after updating an exchange-rate record."""

    source_currency: str
    target_currency: str
    rate_value: Decimal
    created_at: datetime


class UpdateExchangeRateUseCase:
    """Update an existing active exchange-rate record for a currency pair."""

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize the use case with an exchange-rate repository."""
        self._repository = repository

    async def execute(self, command: UpdateExchangeRateCommand) -> UpdateExchangeRateResult:
        """Validate input, update storage, and return updated record data."""
        user_id = normalize_user_id(command.user_id)
        exchange_rate = self._build_exchange_rate(command)
        await self._repository.update(user_id, exchange_rate)
        return UpdateExchangeRateResult(
            source_currency=exchange_rate.source_currency.value,
            target_currency=exchange_rate.target_currency.value,
            rate_value=exchange_rate.rate_value,
            created_at=exchange_rate.created_at,
        )

    def _build_exchange_rate(self, command: UpdateExchangeRateCommand) -> ExchangeRate:
        """Translate update command into a validated domain entity."""
        if command.created_at is None:
            return ExchangeRate(
                source_currency=CurrencyCode(command.source_currency),
                target_currency=CurrencyCode(command.target_currency),
                rate_value=command.rate_value,
            )
        return ExchangeRate(
            source_currency=CurrencyCode(command.source_currency),
            target_currency=CurrencyCode(command.target_currency),
            rate_value=command.rate_value,
            created_at=command.created_at,
        )

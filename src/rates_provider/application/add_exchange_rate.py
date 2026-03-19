"""Application use case for adding exchange-rate records."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


@dataclass(frozen=True, slots=True)
class AddExchangeRateCommand:
    """Input data required to add an exchange-rate record."""

    source_currency: str
    target_currency: str
    rate_value: Decimal
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AddExchangeRateResult:
    """Output data returned after adding an exchange-rate record."""

    source_currency: str
    target_currency: str
    rate_value: Decimal
    created_at: datetime


class AddExchangeRateUseCase:
    """Create and persist a new exchange-rate record."""

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize the use case with an exchange-rate repository."""
        self._repository = repository

    async def execute(self, command: AddExchangeRateCommand) -> AddExchangeRateResult:
        """Validate, persist, and return a newly added exchange-rate record."""
        exchange_rate = self._build_exchange_rate(command)
        await self._repository.add(exchange_rate)
        return AddExchangeRateResult(
            source_currency=exchange_rate.source_currency.value,
            target_currency=exchange_rate.target_currency.value,
            rate_value=exchange_rate.rate_value,
            created_at=exchange_rate.created_at,
        )

    def _build_exchange_rate(self, command: AddExchangeRateCommand) -> ExchangeRate:
        """Translate the application command into a validated domain entity."""
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

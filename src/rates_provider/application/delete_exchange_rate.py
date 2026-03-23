"""Application use case for soft-deleting active exchange-rate records."""

from dataclasses import dataclass

from rates_provider.application._validation import normalize_currency_code, normalize_user_id
from rates_provider.domain.exchange_rate import CurrencyCode
from rates_provider.domain.repositories import ExchangeRateRepository


@dataclass(frozen=True, slots=True)
class DeleteExchangeRateCommand:
    """Input data required to soft-delete an exchange-rate record."""

    user_id: str
    source_currency: str
    target_currency: str


class DeleteExchangeRateUseCase:
    """Soft-delete an existing active exchange-rate record for a currency pair."""

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize the use case with an exchange-rate repository."""
        self._repository = repository

    async def execute(self, command: DeleteExchangeRateCommand) -> None:
        """Validate input and soft-delete exchange rate for the given pair."""
        user_id = normalize_user_id(command.user_id)
        source_currency = CurrencyCode(
            normalize_currency_code(command.source_currency))
        target_currency = CurrencyCode(
            normalize_currency_code(command.target_currency))
        await self._repository.delete(user_id, source_currency, target_currency)

"""Tests for the delete-exchange-rate application use case."""

import asyncio
from collections.abc import Sequence

import pytest

from modules.user_rates.application.delete_exchange_rate import (
    DeleteExchangeRateCommand,
    DeleteExchangeRateUseCase,
)
from modules.user_rates.domain.exchange_rate import CurrencyCode, ExchangeRate
from modules.user_rates.domain.repositories import ExchangeRateRepository


class RecordingExchangeRateRepository(ExchangeRateRepository):
    """In-memory test double capturing delete requests."""

    def __init__(self) -> None:
        """Initialize recording fields for repository interactions."""
        self.deleted_pairs: list[tuple[str, CurrencyCode, CurrencyCode]] = []

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Add operation is unsupported for this delete test double."""
        raise NotImplementedError

    async def update(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Update operation is unsupported for this delete test double."""
        raise NotImplementedError

    async def delete(
        self,
        user_id: str,
        source_currency: CurrencyCode,
        target_currency: CurrencyCode,
    ) -> None:
        """Record delete request for assertion in tests."""
        self.deleted_pairs.append((user_id, source_currency, target_currency))

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """List operation is unsupported for this delete test double."""
        raise NotImplementedError


def test_delete_exchange_rate_normalizes_and_forwards_pair_to_repository() -> None:
    """Use case should normalize user and currencies before repository call."""
    repository = RecordingExchangeRateRepository()
    use_case = DeleteExchangeRateUseCase(repository)

    asyncio.run(
        use_case.execute(
            DeleteExchangeRateCommand(
                user_id="  user-1  ",
                source_currency="usd",
                target_currency="eur",
            )
        )
    )

    user_id, source_currency, target_currency = repository.deleted_pairs[0]
    assert user_id == "user-1"
    assert source_currency == CurrencyCode("USD")
    assert target_currency == CurrencyCode("EUR")


def test_delete_exchange_rate_rejects_blank_user_id() -> None:
    """Use case should reject blank user id values."""
    repository = RecordingExchangeRateRepository()
    use_case = DeleteExchangeRateUseCase(repository)

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(
            use_case.execute(
                DeleteExchangeRateCommand(
                    user_id="   ",
                    source_currency="USD",
                    target_currency="EUR",
                )
            )
        )

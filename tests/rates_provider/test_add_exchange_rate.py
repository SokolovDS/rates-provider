"""Tests for the add-exchange-rate application use case."""

import asyncio
from collections.abc import Sequence
from decimal import Decimal

import pytest

from rates_provider.application.add_exchange_rate import (
    AddExchangeRateCommand,
    AddExchangeRateUseCase,
)
from rates_provider.domain.exceptions import IdenticalCurrencyPairError
from rates_provider.domain.exchange_rate import ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class RecordingExchangeRateRepository(ExchangeRateRepository):
    """In-memory test double capturing added exchange rates."""

    def __init__(self) -> None:
        """Initialize the recording repository."""
        self.added_rates: list[tuple[str, ExchangeRate]] = []

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Store the exchange rate in insertion order."""
        self.added_rates.append((user_id, exchange_rate))

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return all previously added rates."""
        return tuple(rate for rate_user_id, rate in self.added_rates if rate_user_id == user_id)


def test_add_exchange_rate_returns_normalized_result() -> None:
    """Use case should normalize input and return the stored exchange rate data."""
    repository = RecordingExchangeRateRepository()
    use_case = AddExchangeRateUseCase(repository)

    result = asyncio.run(
        use_case.execute(
            AddExchangeRateCommand(
                user_id="user-1",
                source_currency="usd",
                target_currency="eur",
                rate_value=Decimal("90.50"),
            )
        )
    )

    assert result.source_currency == "USD"
    assert result.target_currency == "EUR"
    assert result.rate_value == Decimal("90.50")
    assert len(repository.added_rates) == 1
    assert repository.added_rates[0][0] == "user-1"


def test_add_exchange_rate_keeps_history_for_same_pair() -> None:
    """Use case should append repeated additions for the same pair instead of overwriting."""
    repository = RecordingExchangeRateRepository()
    use_case = AddExchangeRateUseCase(repository)

    asyncio.run(
        use_case.execute(
            AddExchangeRateCommand(
                user_id="user-1",
                source_currency="USD",
                target_currency="EUR",
                rate_value=Decimal("90.50"),
            )
        )
    )
    asyncio.run(
        use_case.execute(
            AddExchangeRateCommand(
                user_id="user-1",
                source_currency="USD",
                target_currency="EUR",
                rate_value=Decimal("91.10"),
            )
        )
    )

    assert [rate.rate_value for _, rate in repository.added_rates] == [
        Decimal("90.50"),
        Decimal("91.10"),
    ]


def test_add_exchange_rate_raises_for_invalid_input() -> None:
    """Use case should surface domain validation errors for invalid input."""
    repository = RecordingExchangeRateRepository()
    use_case = AddExchangeRateUseCase(repository)

    with pytest.raises(IdenticalCurrencyPairError, match="must differ"):
        asyncio.run(
            use_case.execute(
                AddExchangeRateCommand(
                    user_id="user-1",
                    source_currency="USD",
                    target_currency="USD",
                    rate_value=Decimal("90.50"),
                )
            )
        )


def test_add_exchange_rate_normalizes_user_id_before_repository_call() -> None:
    """Use case should trim user id before passing it to repository."""
    repository = RecordingExchangeRateRepository()
    use_case = AddExchangeRateUseCase(repository)

    asyncio.run(
        use_case.execute(
            AddExchangeRateCommand(
                user_id="  user-1  ",
                source_currency="USD",
                target_currency="EUR",
                rate_value=Decimal("90.50"),
            )
        )
    )

    assert repository.added_rates[0][0] == "user-1"


def test_add_exchange_rate_rejects_blank_user_id() -> None:
    """Use case should reject blank user id values."""
    repository = RecordingExchangeRateRepository()
    use_case = AddExchangeRateUseCase(repository)

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(
            use_case.execute(
                AddExchangeRateCommand(
                    user_id="   ",
                    source_currency="USD",
                    target_currency="EUR",
                    rate_value=Decimal("90.50"),
                )
            )
        )

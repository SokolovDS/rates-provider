"""Tests for the add-exchange-rate application use case."""

import asyncio
from collections.abc import Sequence
from decimal import Decimal

import pytest

from modules.user_rates.application.add_exchange_rate import (
    AddExchangeRateCommand,
    AddExchangeRateUseCase,
)
from modules.user_rates.domain.exceptions import IdenticalCurrencyPairError
from modules.user_rates.domain.exchange_rate import CurrencyCode, ExchangeRate
from modules.user_rates.domain.repositories import ExchangeRateRepository


class RecordingExchangeRateRepository(ExchangeRateRepository):
    """In-memory test double capturing latest-only upsert behavior."""

    def __init__(self) -> None:
        """Initialize the recording repository."""
        self.rates_by_pair: dict[tuple[str, str, str], ExchangeRate] = {}

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Store or replace exchange rate by user-scoped pair."""
        key = (
            user_id,
            exchange_rate.source_currency.value,
            exchange_rate.target_currency.value,
        )
        self.rates_by_pair[key] = exchange_rate

    async def update(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Update operation is unsupported for add use-case test double."""
        raise NotImplementedError

    async def delete(
        self,
        user_id: str,
        source_currency: CurrencyCode,
        target_currency: CurrencyCode,
    ) -> None:
        """Delete operation is unsupported for add use-case test double."""
        raise NotImplementedError

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return all rates for requested user."""
        return tuple(
            exchange_rate
            for (rate_user_id, _, _), exchange_rate in self.rates_by_pair.items()
            if rate_user_id == user_id
        )


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
    assert len(repository.rates_by_pair) == 1
    assert ("user-1", "USD", "EUR") in repository.rates_by_pair


def test_add_exchange_rate_overwrites_existing_pair_with_latest_value() -> None:
    """Use case should keep only latest value for the same currency pair."""
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

    stored_rate = repository.rates_by_pair[("user-1", "USD", "EUR")]
    assert stored_rate.rate_value == Decimal("91.10")


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

    assert ("user-1", "USD", "EUR") in repository.rates_by_pair


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

"""Tests for the list-exchange-rates application use case."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from rates_provider.application.list_exchange_rates import ListExchangeRatesUseCase
from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class PreloadedExchangeRateRepository(ExchangeRateRepository):
    """Repository test double returning predefined exchange-rate records."""

    def __init__(self, exchange_rates: Sequence[ExchangeRate]) -> None:
        """Initialize repository state with predefined records."""
        self._exchange_rates = tuple(exchange_rates)

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Append operation is unsupported for this read-only test double."""
        raise NotImplementedError

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return all predefined exchange rates in insertion order."""
        return self._exchange_rates


def test_list_exchange_rates_returns_empty_result_when_repository_is_empty() -> None:
    """Use case should return an empty collection when no rates are stored."""
    repository = PreloadedExchangeRateRepository(exchange_rates=[])
    use_case = ListExchangeRatesUseCase(repository)

    result = asyncio.run(use_case.execute(user_id="user-1"))

    assert result.exchange_rates == tuple()


def test_list_exchange_rates_returns_all_records_in_insertion_order() -> None:
    """Use case should expose all stored records preserving repository order."""
    first_timestamp = datetime(2026, 1, 10, 12, 30, tzinfo=UTC)
    second_timestamp = datetime(2026, 1, 11, 8, 15, tzinfo=UTC)
    first_rate = ExchangeRate(
        source_currency=CurrencyCode("usd"),
        target_currency=CurrencyCode("eur"),
        rate_value=Decimal("90.50"),
        created_at=first_timestamp,
    )
    second_rate = ExchangeRate(
        source_currency=CurrencyCode("eur"),
        target_currency=CurrencyCode("rub"),
        rate_value=Decimal("100.10"),
        created_at=second_timestamp,
    )

    repository = PreloadedExchangeRateRepository(
        exchange_rates=[first_rate, second_rate])
    use_case = ListExchangeRatesUseCase(repository)

    result = asyncio.run(use_case.execute(user_id="user-1"))

    assert result.exchange_rates[0].source_currency == "USD"
    assert result.exchange_rates[0].target_currency == "EUR"
    assert result.exchange_rates[0].rate_value == Decimal("90.50")
    assert result.exchange_rates[0].created_at == first_timestamp
    assert result.exchange_rates[1].source_currency == "EUR"
    assert result.exchange_rates[1].target_currency == "RUB"
    assert result.exchange_rates[1].rate_value == Decimal("100.10")
    assert result.exchange_rates[1].created_at == second_timestamp


def test_list_exchange_rates_passes_user_id_to_repository() -> None:
    """Use case should request records for the current user only."""

    class _RecordingRepository(ExchangeRateRepository):
        def __init__(self) -> None:
            self.received_user_id: str | None = None

        async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
            raise NotImplementedError

        async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
            self.received_user_id = user_id
            return tuple()

    repository = _RecordingRepository()
    use_case = ListExchangeRatesUseCase(repository)

    result = asyncio.run(use_case.execute(user_id="user-42"))

    assert result.exchange_rates == tuple()
    assert repository.received_user_id == "user-42"


def test_list_exchange_rates_normalizes_user_id_before_repository_call() -> None:
    """Use case should trim user id before asking repository."""

    class _RecordingRepository(ExchangeRateRepository):
        def __init__(self) -> None:
            self.received_user_id: str | None = None

        async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
            raise NotImplementedError

        async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
            self.received_user_id = user_id
            return tuple()

    repository = _RecordingRepository()
    use_case = ListExchangeRatesUseCase(repository)

    asyncio.run(use_case.execute(user_id="  user-42  "))

    assert repository.received_user_id == "user-42"


def test_list_exchange_rates_rejects_blank_user_id() -> None:
    """Use case should reject blank user id values."""
    repository = PreloadedExchangeRateRepository(exchange_rates=[])
    use_case = ListExchangeRatesUseCase(repository)

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(use_case.execute(user_id="   "))

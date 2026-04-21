"""Tests for listing selectable currencies for exchange-path Telegram flows."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from modules.market_rates.contracts.dtos import MarketRateEntry
from modules.market_rates.contracts.reader_port import MarketRatesReaderPort
from modules.quote_engine.application.list_selectable_currencies import (
    ListSelectableCurrenciesCommand,
    ListSelectableCurrenciesUseCase,
)
from modules.user_rates.contracts.dtos import RateEntry
from modules.user_rates.contracts.reader_port import UserRatesReaderPort


class PreloadedUserRatesReader(UserRatesReaderPort):
    """Reader test double returning predefined user-scoped rate entries."""

    def __init__(self, rates_by_user: dict[str, Sequence[RateEntry]]) -> None:
        """Initialize reader state with user-scoped rate entries."""
        self._rates_by_user = {
            user_id: tuple(entries)
            for user_id, entries in rates_by_user.items()
        }

    async def list_rates(self, user_id: str) -> Sequence[RateEntry]:
        """Return all predefined rates for a specific user."""
        return self._rates_by_user.get(user_id, tuple())


class PreloadedMarketRatesReader(MarketRatesReaderPort):
    """Reader test double returning predefined market rate entries."""

    def __init__(self, rates: Sequence[MarketRateEntry] = ()) -> None:
        """Initialize reader with a fixed set of market rate entries."""
        self._rates = tuple(rates)

    async def list_rates(self) -> Sequence[MarketRateEntry]:
        """Return all predefined market rates."""
        return self._rates


def _market_entry(source: str, target: str, value: str) -> MarketRateEntry:
    """Build deterministic market rate entry for test scenarios."""
    return MarketRateEntry(
        source_currency=source,
        target_currency=target,
        rate_value=Decimal(value),
    )


def _rate_entry(source: str, target: str, value: str) -> RateEntry:
    """Build deterministic rate entry for test scenarios."""
    return RateEntry(
        source_currency=source,
        target_currency=target,
        rate_value=Decimal(value),
        created_at=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
    )


def test_list_selectable_source_currencies_merges_and_deduplicates_codes() -> None:
    """Source selection should return unique currencies from merged rate graph."""
    user_reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "USD", "80"),
                _rate_entry("usd", "EUR", "0.9"),
            ]
        }
    )
    market_reader = PreloadedMarketRatesReader(
        [
            _market_entry("THB", "USD", "0.03"),
            _market_entry("EUR", "THB", "40"),
        ]
    )
    use_case = ListSelectableCurrenciesUseCase(user_reader, market_reader)

    result = asyncio.run(
        use_case.execute(ListSelectableCurrenciesCommand(user_id="user-1"))
    )

    assert result.currencies == ("EUR", "RUB", "THB", "USD")


def test_list_selectable_target_currencies_returns_only_reachable_codes() -> None:
    """Target selection should include only currencies reachable from source."""
    user_reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "USD", "80"),
                _rate_entry("USD", "EUR", "0.9"),
            ]
        }
    )
    market_reader = PreloadedMarketRatesReader(
        [
            _market_entry("THB", "USD", "0.03"),
            _market_entry("EUR", "THB", "40"),
            _market_entry("JPY", "AUD", "0.01"),
        ]
    )
    use_case = ListSelectableCurrenciesUseCase(user_reader, market_reader)

    result = asyncio.run(
        use_case.execute(
            ListSelectableCurrenciesCommand(
                user_id="user-1",
                source_currency="rub",
            )
        )
    )

    assert result.currencies == ("EUR", "THB", "USD")


def test_list_selectable_target_currencies_excludes_selected_source() -> None:
    """Target selection should never repeat the already selected source code."""
    user_reader = PreloadedUserRatesReader(
        {"user-1": [_rate_entry("RUB", "USD", "80")]}
    )
    use_case = ListSelectableCurrenciesUseCase(
        user_reader,
        PreloadedMarketRatesReader(),
    )

    result = asyncio.run(
        use_case.execute(
            ListSelectableCurrenciesCommand(
                user_id="user-1",
                source_currency="RUB",
            )
        )
    )

    assert result.currencies == ("USD",)


def test_list_selectable_target_currencies_returns_empty_for_unknown_source() -> None:
    """Target selection should be empty when the source code has no outgoing paths."""
    user_reader = PreloadedUserRatesReader(
        {"user-1": [_rate_entry("RUB", "USD", "80")]}
    )
    use_case = ListSelectableCurrenciesUseCase(
        user_reader,
        PreloadedMarketRatesReader(),
    )

    result = asyncio.run(
        use_case.execute(
            ListSelectableCurrenciesCommand(
                user_id="user-1",
                source_currency="THB",
            )
        )
    )

    assert result.currencies == tuple()


def test_list_selectable_source_currencies_returns_empty_for_empty_graph() -> None:
    """Source selection should be empty when neither user nor market rates exist."""
    use_case = ListSelectableCurrenciesUseCase(
        PreloadedUserRatesReader({"user-1": tuple()}),
        PreloadedMarketRatesReader(),
    )

    result = asyncio.run(
        use_case.execute(ListSelectableCurrenciesCommand(user_id="user-1"))
    )

    assert result.currencies == tuple()

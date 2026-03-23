"""Tests for selected-rate scene text formatting and empty-state handling."""

from datetime import UTC, datetime
from decimal import Decimal

from rates_provider.application.list_exchange_rates import (
    ExchangeRateListItem,
    ListExchangeRatesResult,
)
from rates_provider.infrastructure.telegram_bot.scenes.selected_rate import (
    _build_selected_pair_lines,
)


def test_build_selected_pair_lines_shows_selected_pair_and_action_prompt() -> None:
    """Selected pair state should include pair details and action hint."""
    selected_item = ExchangeRateListItem(
        source_currency="USD",
        target_currency="EUR",
        rate_value=Decimal("90.50"),
        created_at=datetime(2026, 3, 19, 11, 0, tzinfo=UTC),
    )
    result = ListExchangeRatesResult(exchange_rates=(selected_item,))

    assert _build_selected_pair_lines(result, "USD", "EUR") == [
        "Курсы обмена",
        "Пара: USD -> EUR",
        "Текущий курс: 90.50 (2026.03.19 11:00:00 UTC)",
        "",
        "Выбери действие:",
    ]


def test_build_selected_pair_lines_returns_not_found_message() -> None:
    """Selected pair state should show explicit not-found text for stale pair."""
    item = ExchangeRateListItem(
        source_currency="USD",
        target_currency="EUR",
        rate_value=Decimal("90.50"),
        created_at=datetime(2026, 3, 19, 11, 0, tzinfo=UTC),
    )
    result = ListExchangeRatesResult(exchange_rates=(item,))

    assert _build_selected_pair_lines(result, "EUR", "USD") == [
        "Курсы обмена",
        "",
        "Выбранная валютная пара не найдена.",
    ]

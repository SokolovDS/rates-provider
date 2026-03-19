"""Tests for Telegram list-rates scene text formatting."""

from datetime import UTC, datetime
from decimal import Decimal

from rates_provider.application.list_exchange_rates import (
    ExchangeRateListItem,
    ListExchangeRatesResult,
)
from rates_provider.infrastructure.telegram_bot.scenes.list_rates import (
    _build_list_rates_lines,
    _format_created_at,
    _format_rate_value,
)


def test_format_rate_value_uses_plain_decimal_notation() -> None:
    """List scene should render decimals without scientific notation."""
    assert _format_rate_value(Decimal("80")) == "80"
    assert _format_rate_value(Decimal("90.50")) == "90.50"


def test_format_created_at_uses_utc_timestamp() -> None:
    """List scene should render timestamps in compact UTC format."""
    created_at = datetime(2026, 3, 19, 11, 0, tzinfo=UTC)

    assert _format_created_at(created_at) == "2026.03.19 11:00:00 UTC"


def test_build_list_rates_lines_returns_empty_state() -> None:
    """List scene should show an explicit empty-state message when no rates exist."""
    result = ListExchangeRatesResult(exchange_rates=tuple())

    assert _build_list_rates_lines(result) == [
        "Курсы обмена",
        "",
        "Курсы пока не добавлены.",
    ]


def test_build_list_rates_lines_shows_newest_first() -> None:
    """List scene should show newest stored rates first using arrow formatting."""
    first_item = ExchangeRateListItem(
        source_currency="USD",
        target_currency="EUR",
        rate_value=Decimal("80"),
        created_at=datetime(2026, 3, 19, 10, 0, tzinfo=UTC),
    )
    second_item = ExchangeRateListItem(
        source_currency="EUR",
        target_currency="RUB",
        rate_value=Decimal("90.50"),
        created_at=datetime(2026, 3, 19, 11, 0, tzinfo=UTC),
    )
    result = ListExchangeRatesResult(exchange_rates=(first_item, second_item))

    assert _build_list_rates_lines(result) == [
        "Курсы обмена",
        "",
        "EUR -> RUB = 90.50 (2026.03.19 11:00:00 UTC)",
        "USD -> EUR = 80 (2026.03.19 10:00:00 UTC)",
    ]

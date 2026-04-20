"""Tests for Telegram market-rates scene text formatting."""

from decimal import Decimal

from interfaces.telegram_bot.scenes.market_rates import _build_market_rates_lines
from modules.market_rates.application.list_market_rates import ListMarketRatesResult
from modules.market_rates.contracts.dtos import MarketRateEntry


def _entry(source: str, target: str, value: str) -> MarketRateEntry:
    """Build a MarketRateEntry for test use."""
    return MarketRateEntry(
        source_currency=source,
        target_currency=target,
        rate_value=Decimal(value),
    )


def test_build_market_rates_lines_empty_state() -> None:
    """Scene should show an explicit empty-state message when no rates exist."""
    result = ListMarketRatesResult(exchange_rates=())

    lines = _build_market_rates_lines(result, text_lines=["Рыночные курсы"])

    assert lines == ["Рыночные курсы", "", "Данные отсутствуют."]


def test_build_market_rates_lines_single_entry() -> None:
    """Scene should render one group header and one rate line for a single entry."""
    result = ListMarketRatesResult(
        exchange_rates=(_entry("USD", "EUR", "0.92"),))

    lines = _build_market_rates_lines(result, text_lines=["Рыночные курсы"])

    assert lines == ["Рыночные курсы", "", "<b>1 USD</b>", "  = 0.92 EUR"]


def test_build_market_rates_lines_groups_by_source_currency() -> None:
    """Scene should group rate lines under bold source currency headers."""
    result = ListMarketRatesResult(
        exchange_rates=(
            _entry("USD", "EUR", "0.92"),
            _entry("EUR", "USD", "1.08"),
            _entry("USD", "RUB", "90"),
        )
    )

    lines = _build_market_rates_lines(result, text_lines=["Рыночные курсы"])

    assert lines == [
        "Рыночные курсы",
        "",
        "<b>1 EUR</b>",
        "  = 1.08 USD",
        "",
        "<b>1 USD</b>",
        "  = 0.92 EUR",
        "  = 90 RUB",
    ]


def test_build_market_rates_lines_integer_rate_uses_plain_notation() -> None:
    """Scene should render whole-number rates without decimal point."""
    result = ListMarketRatesResult(
        exchange_rates=(_entry("USD", "RUB", "90"),))

    lines = _build_market_rates_lines(result, text_lines=["Рыночные курсы"])

    assert "  = 90 RUB" in lines


def test_build_market_rates_lines_sorts_targets_within_group() -> None:
    """Targets within a source group should appear in alphabetical order."""
    result = ListMarketRatesResult(
        exchange_rates=(
            _entry("USD", "RUB", "90"),
            _entry("USD", "EUR", "0.92"),
        )
    )

    lines = _build_market_rates_lines(result, text_lines=["Рыночные курсы"])

    eur_idx = lines.index("  = 0.92 EUR")
    rub_idx = lines.index("  = 90 RUB")
    assert eur_idx < rub_idx

"""Tests for Telegram exchange-paths scene formatting helpers."""

from decimal import Decimal

from rates_provider.application.compute_exchange_paths import (
    ComputeExchangePathsResult,
    ComputeReceivedAmountResult,
    ComputeRequiredSourceAmountResult,
    ExchangePathItem,
    ExchangeTargetAmountItem,
    RequiredSourceAmountItem,
)
from rates_provider.infrastructure.telegram_bot.scenes.exchange_paths import (
    build_exchange_paths_lines,
    build_received_amount_lines,
    build_required_source_amount_lines,
    format_amount_value,
    format_deviation_percent,
    format_rate_value,
)


def test_format_rate_value_uses_plain_decimal_notation() -> None:
    """Rate formatter should round Telegram display to at most two decimals."""
    assert format_rate_value(Decimal("80")) == "80"
    assert format_rate_value(Decimal("90.50")) == "90.50"
    assert format_rate_value(Decimal("90.555")) == "90.56"


def test_format_amount_value_uses_plain_decimal_notation() -> None:
    """Amount formatter should round Telegram display to at most two decimals."""
    assert format_amount_value(Decimal("80")) == "80"
    assert format_amount_value(Decimal("90.505")) == "90.51"


def test_format_deviation_percent_shows_signed_percent() -> None:
    """Deviation formatter should keep explicit sign for non-zero values."""
    assert format_deviation_percent(Decimal("0")) == "0%"
    assert format_deviation_percent(Decimal("-12.5")) == "-12.50%"
    assert format_deviation_percent(Decimal("-12.555")) == "-12.56%"


def test_build_exchange_paths_lines_returns_empty_state() -> None:
    """Scene helper should render explicit empty-state lines."""
    result = ComputeExchangePathsResult(
        source_currency="RUB",
        target_currency="THB",
        best_rate=Decimal("0"),
        paths=tuple(),
    )

    assert build_exchange_paths_lines(result) == [
        "Маршруты обмена RUB -> THB",
        "",
        "Маршруты не найдены.",
    ]


def test_build_exchange_paths_lines_renders_routes_in_given_order() -> None:
    """Scene helper should render each route with rate and signed deviation."""
    result = ComputeExchangePathsResult(
        source_currency="RUB",
        target_currency="THB",
        best_rate=Decimal("60000"),
        paths=(
            ExchangePathItem(
                currencies=("RUB", "USD", "CNY", "THB"),
                effective_rate=Decimal("60000"),
                deviation_percent=Decimal("0"),
            ),
            ExchangePathItem(
                currencies=("RUB", "USD", "THB"),
                effective_rate=Decimal("1600"),
                deviation_percent=Decimal("-97.3333"),
            ),
        ),
    )

    assert build_exchange_paths_lines(result) == [
        "Маршруты обмена RUB -> THB",
        "",
        "RUB -> USD -> CNY -> THB = 60000 (0%)",
        "RUB -> USD -> THB = 1600 (-97.33%)",
    ]


def test_build_received_amount_lines_renders_routes_in_given_order() -> None:
    """Formatter should render received target amount for each route."""
    result = ComputeReceivedAmountResult(
        source_currency="RUB",
        target_currency="THB",
        source_amount=Decimal("2"),
        best_target_amount=Decimal("120000"),
        paths=(
            ExchangeTargetAmountItem(
                currencies=("RUB", "USD", "CNY", "THB"),
                effective_rate=Decimal("60000"),
                target_amount=Decimal("120000"),
                deviation_percent=Decimal("0"),
            ),
            ExchangeTargetAmountItem(
                currencies=("RUB", "THB"),
                effective_rate=Decimal("5"),
                target_amount=Decimal("10"),
                deviation_percent=Decimal("-99.9916666667"),
            ),
        ),
    )

    assert build_received_amount_lines(result) == [
        "Получишь за 2 RUB -> THB",
        "",
        "RUB -> USD -> CNY -> THB = 120000 THB (курс: 60000, 0%)",
        "RUB -> THB = 10 THB (курс: 5, -99.99%)",
    ]


def test_build_required_source_amount_lines_renders_routes_in_given_order() -> None:
    """Formatter should render required source amount for each route."""
    result = ComputeRequiredSourceAmountResult(
        source_currency="RUB",
        target_currency="THB",
        target_amount=Decimal("600"),
        best_source_amount=Decimal("0.01"),
        paths=(
            RequiredSourceAmountItem(
                currencies=("RUB", "USD", "CNY", "THB"),
                effective_rate=Decimal("60000"),
                source_amount=Decimal("0.01"),
                deviation_percent=Decimal("0"),
            ),
            RequiredSourceAmountItem(
                currencies=("RUB", "THB"),
                effective_rate=Decimal("5"),
                source_amount=Decimal("120"),
                deviation_percent=Decimal("-99.9916666667"),
            ),
        ),
    )

    assert build_required_source_amount_lines(result) == [
        "Нужно для получения 600 THB из RUB",
        "",
        "RUB -> USD -> CNY -> THB = 0.01 RUB (курс: 60000, 0%)",
        "RUB -> THB = 120 RUB (курс: 5, -99.99%)",
    ]

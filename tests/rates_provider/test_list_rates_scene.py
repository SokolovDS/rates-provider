"""Tests for Telegram list-rates scene text formatting."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from rates_provider.application.list_exchange_rates import (
    ExchangeRateListItem,
    ListExchangeRatesResult,
)
from rates_provider.infrastructure.telegram_bot.callbacks.my_rates import (
    RatePairCallback,
)
from rates_provider.infrastructure.telegram_bot.scenes.my_rates.list_rates import (
    _build_list_rates_lines,
    _build_pairs_keyboard_rows,
)
from rates_provider.infrastructure.telegram_bot.scenes.shared.formatting import (
    format_created_at_utc,
    format_rate_value_plain,
)


def test_format_rate_value_uses_plain_decimal_notation() -> None:
    """List scene should render decimals without scientific notation."""
    assert format_rate_value_plain(Decimal("80")) == "80"
    assert format_rate_value_plain(Decimal("90.50")) == "90.50"


def test_format_created_at_uses_utc_timestamp() -> None:
    """List scene should render timestamps in compact UTC format."""
    created_at = datetime(2026, 3, 19, 11, 0, tzinfo=UTC)

    assert format_created_at_utc(created_at) == "2026.03.19 11:00:00 UTC"


def test_build_list_rates_lines_returns_empty_state() -> None:
    """List scene should show an explicit empty-state message when no rates exist."""
    result = ListExchangeRatesResult(exchange_rates=tuple())

    assert _build_list_rates_lines(
        result,
        text_lines=["Курсы обмена"],
        prompt_text="Выбери валютную пару из списка ниже.",
    ) == [
        "Курсы обмена",
        "",
        "Курсы пока не добавлены.",
    ]


def test_build_list_rates_lines_preserves_latest_pair_order() -> None:
    """List scene should render instruction text for pair-button selection."""
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

    assert _build_list_rates_lines(
        result,
        text_lines=["Курсы обмена"],
        prompt_text="Выбери валютную пару из списка ниже.",
    ) == [
        "Курсы обмена",
        "",
        "Выбери валютную пару из списка ниже.",
    ]


def test_build_pairs_keyboard_rows_contains_one_button_per_pair() -> None:
    """Pair list should render one callback button per pair with rate value."""
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

    rows = _build_pairs_keyboard_rows(result)

    assert rows[0][0].text == "USD -> EUR = 80"
    assert rows[0][0].callback_data == RatePairCallback(
        source_currency="USD",
        target_currency="EUR",
    ).pack()
    assert rows[1][0].text == "EUR -> RUB = 90.50"
    assert rows[1][0].callback_data == RatePairCallback(
        source_currency="EUR",
        target_currency="RUB",
    ).pack()


def test_pair_callback_data_roundtrip() -> None:
    """Callback contract should encode and decode pair callback payloads."""
    callback_data = RatePairCallback(
        source_currency="USD",
        target_currency="EUR",
    ).pack()
    unpacked = RatePairCallback.unpack(callback_data)

    assert unpacked.source_currency == "USD"
    assert unpacked.target_currency == "EUR"


def test_pair_callback_data_parser_rejects_invalid_payload() -> None:
    """Callback contract should reject payload with unexpected format."""
    with pytest.raises(TypeError, match="takes 2 arguments but 1"):
        RatePairCallback.unpack("rate_pair:USD")

    with pytest.raises(ValueError, match="unknown"):
        RatePairCallback.unpack("unknown:USD:EUR")

"""Tests for Telegram list-rates scene text formatting."""

from datetime import UTC, datetime
from decimal import Decimal

from rates_provider.application.list_exchange_rates import (
    ExchangeRateListItem,
    ListExchangeRatesResult,
)
from rates_provider.infrastructure.telegram_bot.scenes.my_rates.list_rates import (
    ADD_RATE_CALLBACK_DATA,
    _build_list_rates_lines,
    _build_pair_callback_data,
    _build_pairs_keyboard_rows,
    _parse_pair_callback_data,
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

    assert _build_list_rates_lines(result) == [
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

    assert _build_list_rates_lines(result) == [
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
    assert rows[0][0].callback_data == "rate_pair:USD:EUR"
    assert rows[1][0].text == "EUR -> RUB = 90.50"
    assert rows[1][0].callback_data == "rate_pair:EUR:RUB"


def test_list_scene_exposes_add_rate_callback_data_constant() -> None:
    """List scene should expose callback id for add-rate action button."""
    assert ADD_RATE_CALLBACK_DATA == "list_add_rate"


def test_pair_callback_data_roundtrip() -> None:
    """Scene helpers should encode and decode pair callback payloads."""
    callback_data = _build_pair_callback_data("rate_edit", "USD", "EUR")

    assert callback_data == "rate_edit:USD:EUR"
    assert _parse_pair_callback_data(
        callback_data, "rate_edit") == ("USD", "EUR")


def test_pair_callback_data_parser_rejects_invalid_payload() -> None:
    """Scene helper should reject callback payload with unexpected format."""
    assert _parse_pair_callback_data("rate_edit:USD", "rate_edit") is None
    assert _parse_pair_callback_data("unknown:USD:EUR", "rate_edit") is None

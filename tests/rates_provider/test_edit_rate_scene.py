"""Tests for edit-rate scene validation helpers and error mapping."""

from decimal import Decimal, InvalidOperation

import pytest

from rates_provider.domain.exceptions import DomainValidationError, NonPositiveRateValueError
from rates_provider.infrastructure.telegram_bot.scenes.edit_rate import (
    edit_error_message,
)
from rates_provider.infrastructure.telegram_bot.scenes.formatting import (
    format_rate_value_plain,
    parse_rate_value,
)


def test_parse_rate_accepts_decimal_input() -> None:
    """Rate parser should convert numeric text to Decimal values."""
    assert parse_rate_value("90.50") == Decimal("90.50")
    assert parse_rate_value("-1") == Decimal("-1")
    with pytest.raises(InvalidOperation):
        parse_rate_value("abc")


def test_format_rate_value_uses_plain_decimal_notation() -> None:
    """Rate formatter should avoid scientific notation for integer decimals."""
    assert format_rate_value_plain(Decimal("80")) == "80"
    assert format_rate_value_plain(Decimal("90.50")) == "90.50"


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (
            NonPositiveRateValueError("not positive"),
            "Ошибка: курс должен быть положительным числом, например 90.50.",
        ),
        (
            InvalidOperation(),
            "Ошибка: курс должен быть положительным числом, например 90.50.",
        ),
        (
            ValueError("not found"),
            "Ошибка: выбранная валютная пара не найдена.",
        ),
        (
            DomainValidationError("generic"),
            "Ошибка: не удалось изменить курс. Проверьте введенные данные.",
        ),
    ],
)
def test_edit_error_message_mapping(error: Exception, expected_message: str) -> None:
    """Edit scene should map domain and parsing errors to user-friendly text."""
    assert edit_error_message(error) == expected_message

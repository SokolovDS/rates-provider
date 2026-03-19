"""Tests for add-rate scene validation helpers and domain error mapping."""

from decimal import Decimal, InvalidOperation

import pytest

from rates_provider.domain.exceptions import (
    DomainValidationError,
    IdenticalCurrencyPairError,
    InvalidCurrencyCodeError,
    NonPositiveRateValueError,
)
from rates_provider.infrastructure.telegram_bot.scenes.add_rate import (
    _domain_error_message,
    _format_rate_value,
    _parse_rate,
)


def test_parse_rate_accepts_decimal_input() -> None:
    """Rate parser should convert numeric text to Decimal values."""
    assert _parse_rate("90.50") == Decimal("90.50")
    assert _parse_rate("-1") == Decimal("-1")
    with pytest.raises(InvalidOperation):
        _parse_rate("abc")


def test_format_rate_value_uses_plain_decimal_notation() -> None:
    """Rate formatter should avoid scientific notation for integer decimals."""
    assert _format_rate_value(Decimal("80")) == "80"
    assert _format_rate_value(Decimal("90.50")) == "90.50"


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (
            InvalidCurrencyCodeError("bad code"),
            "Ошибка: валюта должна быть из 3 латинских букв, например USD.",
        ),
        (
            IdenticalCurrencyPairError("same pair"),
            "Ошибка: целевая валюта должна отличаться от исходной.",
        ),
        (
            NonPositiveRateValueError("not positive"),
            "Ошибка: курс должен быть положительным числом, например 90.50.",
        ),
        (
            InvalidOperation(),
            "Ошибка: курс должен быть положительным числом, например 90.50.",
        ),
        (
            DomainValidationError("generic"),
            "Ошибка: не удалось сохранить курс. Проверьте введенные данные.",
        ),
    ],
)
def test_domain_error_message_mapping(
    error: Exception,
    expected_message: str,
) -> None:
    """Domain errors should be mapped to user-friendly Russian error messages."""
    assert _domain_error_message(error) == expected_message

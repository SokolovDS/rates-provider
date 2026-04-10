"""Tests for exchange-rate domain primitives."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from modules.user_rates.domain.exceptions import (
    IdenticalCurrencyPairError,
    InvalidCurrencyCodeError,
    NonPositiveRateValueError,
)
from modules.user_rates.domain.exchange_rate import CurrencyCode, ExchangeRate


def test_currency_code_normalizes_to_uppercase() -> None:
    """CurrencyCode should normalize lowercase input to uppercase."""
    currency_code = CurrencyCode("usd")

    assert currency_code.value == "USD"


@pytest.mark.parametrize("raw_value", ["", "US", "USDT", "12A", "EU1", "РУБ"])
def test_currency_code_rejects_invalid_value(raw_value: str) -> None:
    """CurrencyCode should reject values outside the three-letter alphabetic format."""
    with pytest.raises(InvalidCurrencyCodeError, match="currency code"):
        CurrencyCode(raw_value)


def test_exchange_rate_rejects_non_positive_rate() -> None:
    """ExchangeRate should require a positive rate value."""
    with pytest.raises(NonPositiveRateValueError, match="positive"):
        ExchangeRate(
            source_currency=CurrencyCode("USD"),
            target_currency=CurrencyCode("EUR"),
            rate_value=Decimal("0"),
        )


def test_exchange_rate_rejects_same_currency_pair() -> None:
    """ExchangeRate should reject pairs with identical source and target currencies."""
    with pytest.raises(IdenticalCurrencyPairError, match="must differ"):
        ExchangeRate(
            source_currency=CurrencyCode("USD"),
            target_currency=CurrencyCode("USD"),
            rate_value=Decimal("90.50"),
        )


def test_exchange_rate_uses_provided_timestamp() -> None:
    """ExchangeRate should keep the provided timestamp unchanged."""
    created_at = datetime(2026, 3, 17, 12, 0, tzinfo=UTC)

    exchange_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
        created_at=created_at,
    )

    assert exchange_rate.created_at is created_at


def test_exchange_rate_defaults_to_timezone_aware_timestamp() -> None:
    """ExchangeRate should generate a timezone-aware timestamp when omitted."""
    exchange_rate = ExchangeRate(
        source_currency=CurrencyCode("USD"),
        target_currency=CurrencyCode("EUR"),
        rate_value=Decimal("90.50"),
    )

    assert exchange_rate.created_at.tzinfo is UTC

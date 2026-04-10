"""Domain primitives for exchange-rate management."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from .exceptions import (
    IdenticalCurrencyPairError,
    InvalidCurrencyCodeError,
    NaiveTimestampError,
    NonPositiveRateValueError,
)


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    """Normalized ISO-like three-letter currency code."""

    value: str

    def __post_init__(self) -> None:
        """Normalize and validate the currency code."""
        normalized_value = self.value.strip().upper()
        if (
            len(normalized_value) != 3
            or not normalized_value.isascii()
            or not normalized_value.isalpha()
        ):
            message = "A currency code must consist of three alphabetic characters."
            raise InvalidCurrencyCodeError(message)
        object.__setattr__(self, "value", normalized_value)


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Immutable exchange-rate record for a currency pair."""

    source_currency: CurrencyCode
    target_currency: CurrencyCode
    rate_value: Decimal
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate the currency pair, value, and timestamp."""
        if self.source_currency == self.target_currency:
            message = "Exchange-rate currencies must differ."
            raise IdenticalCurrencyPairError(message)
        if self.rate_value <= Decimal("0"):
            message = "Exchange-rate value must be positive."
            raise NonPositiveRateValueError(message)
        if self.created_at.tzinfo is None:
            message = "Exchange-rate timestamp must be timezone-aware."
            raise NaiveTimestampError(message)

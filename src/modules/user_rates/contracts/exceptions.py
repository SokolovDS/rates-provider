"""Public exception types exported by the user_rates contracts layer."""

from modules.user_rates.domain.exceptions import (
    DomainValidationError,
    IdenticalCurrencyPairError,
    InvalidCurrencyCodeError,
    NaiveTimestampError,
    NonPositiveRateValueError,
)

__all__ = [
    "DomainValidationError",
    "IdenticalCurrencyPairError",
    "InvalidCurrencyCodeError",
    "NaiveTimestampError",
    "NonPositiveRateValueError",
]

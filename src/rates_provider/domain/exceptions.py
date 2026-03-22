"""Domain exceptions for exchange-rate invariant violations."""


class DomainValidationError(ValueError):
    """Base class for all domain-level invariant violations."""


class InvalidCurrencyCodeError(DomainValidationError):
    """Raised when a currency code does not meet the three-letter alphabetic format."""


class IdenticalCurrencyPairError(DomainValidationError):
    """Raised when source and target currencies in an exchange-rate pair are identical."""


class NonPositiveRateValueError(DomainValidationError):
    """Raised when an exchange-rate value is zero or negative."""


class NaiveTimestampError(DomainValidationError):
    """Raised when an exchange-rate timestamp is not timezone-aware."""


class NoExchangePathError(DomainValidationError):
    """Raised when no exchange route can be built for source and target currencies."""


class NonPositiveAmountError(DomainValidationError):
    """Raised when requested source or target amount is zero or negative."""

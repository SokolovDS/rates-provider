"""Domain exceptions for quote engine invariant violations."""


class NoExchangePathError(ValueError):
    """Raised when no exchange route can be built for source and target currencies."""


class NonPositiveAmountError(ValueError):
    """Raised when requested source or target amount is zero or negative."""

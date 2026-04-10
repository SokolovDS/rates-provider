"""Shared validation utilities for application use cases."""

from modules.user_rates.domain.exchange_rate import CurrencyCode


def normalize_user_id(user_id: str) -> str:
    """Return normalized user id or raise when it is blank."""
    normalized = user_id.strip()
    if normalized == "":
        message = "User id must not be empty."
        raise ValueError(message)
    return normalized


def normalize_currency_code(value: str) -> str:
    """Return normalized currency code using domain validation rules."""
    return CurrencyCode(value).value

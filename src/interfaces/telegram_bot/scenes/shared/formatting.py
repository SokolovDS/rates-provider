"""Shared formatting helpers for Telegram bot scene output."""

from datetime import UTC, datetime
from decimal import Decimal


def parse_rate_value(value: str) -> Decimal:
    """Parse decimal rate value from user-provided text."""
    return Decimal(value.strip())


def format_rate_value_plain(rate_value: Decimal) -> str:
    """Format Decimal rate without scientific notation."""
    return format(rate_value, "f")


def format_created_at_utc(created_at: datetime) -> str:
    """Format timestamp in compact UTC representation for Telegram UI."""
    utc_timestamp = created_at.astimezone(UTC)
    return utc_timestamp.strftime("%Y.%m.%d %H:%M:%S UTC")

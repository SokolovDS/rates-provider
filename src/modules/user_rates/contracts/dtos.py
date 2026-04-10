"""Public DTOs exported by the user_rates contracts layer."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RateEntry:
    """Public DTO representing a single user-managed exchange-rate record."""

    source_currency: str
    target_currency: str
    rate_value: Decimal
    created_at: datetime

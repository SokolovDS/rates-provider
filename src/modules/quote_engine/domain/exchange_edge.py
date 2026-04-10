"""Internal edge representation for the exchange graph."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExchangeEdge:
    """A directed weighted edge between two currency nodes in the exchange graph."""

    source_currency: str
    target_currency: str
    rate_value: Decimal

"""Application DTOs for the quote engine use cases."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ComputeExchangePathsCommand:
    """Input data required to compute exchange routes."""

    user_id: str
    source_currency: str
    target_currency: str


@dataclass(frozen=True, slots=True)
class ExchangePathItem:
    """A single exchange route with effective rate and deviation from best."""

    currencies: tuple[str, ...]
    effective_rate: Decimal
    deviation_percent: Decimal


@dataclass(frozen=True, slots=True)
class ComputeExchangePathsResult:
    """Output DTO for ranked exchange routes between two currencies."""

    source_currency: str
    target_currency: str
    best_rate: Decimal
    paths: tuple[ExchangePathItem, ...]


@dataclass(frozen=True, slots=True)
class ComputeReceivedAmountCommand:
    """Input data required to compute target amount for a source amount."""

    user_id: str
    source_currency: str
    target_currency: str
    source_amount: Decimal


@dataclass(frozen=True, slots=True)
class ExchangeTargetAmountItem:
    """A single route with effective rate and resulting target amount."""

    currencies: tuple[str, ...]
    effective_rate: Decimal
    target_amount: Decimal
    deviation_percent: Decimal


@dataclass(frozen=True, slots=True)
class ComputeReceivedAmountResult:
    """Output DTO for received target amount across ranked exchange routes."""

    source_currency: str
    target_currency: str
    source_amount: Decimal
    best_target_amount: Decimal
    paths: tuple[ExchangeTargetAmountItem, ...]


@dataclass(frozen=True, slots=True)
class ComputeRequiredSourceAmountCommand:
    """Input data required to compute source amount needed for target result."""

    user_id: str
    source_currency: str
    target_currency: str
    target_amount: Decimal


@dataclass(frozen=True, slots=True)
class RequiredSourceAmountItem:
    """A single route with effective rate and required source amount."""

    currencies: tuple[str, ...]
    effective_rate: Decimal
    source_amount: Decimal
    deviation_percent: Decimal


@dataclass(frozen=True, slots=True)
class ComputeRequiredSourceAmountResult:
    """Output DTO for source amount needed across ranked exchange routes."""

    source_currency: str
    target_currency: str
    target_amount: Decimal
    best_source_amount: Decimal
    paths: tuple[RequiredSourceAmountItem, ...]

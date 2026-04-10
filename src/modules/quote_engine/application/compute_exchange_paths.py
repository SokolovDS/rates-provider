"""Application use cases for computing ranked exchange routes."""

from __future__ import annotations

from decimal import Decimal

from app.shared._validation import normalize_currency_code, normalize_user_id
from modules.quote_engine.application.dtos import (
    ComputeExchangePathsCommand,
    ComputeExchangePathsResult,
    ComputeReceivedAmountCommand,
    ComputeReceivedAmountResult,
    ComputeRequiredSourceAmountCommand,
    ComputeRequiredSourceAmountResult,
    ExchangePathItem,
    ExchangeTargetAmountItem,
    RequiredSourceAmountItem,
)
from modules.quote_engine.domain.exceptions import NoExchangePathError, NonPositiveAmountError
from modules.quote_engine.domain.exchange_edge import ExchangeEdge
from modules.quote_engine.domain.graph import MAX_EXCHANGES_PER_PATH, DiscoveredPath, ExchangeGraph
from modules.user_rates.contracts.dtos import RateEntry
from modules.user_rates.contracts.exceptions import IdenticalCurrencyPairError
from modules.user_rates.contracts.reader_port import UserRatesReaderPort


def _rate_entry_to_edge(entry: RateEntry) -> ExchangeEdge:
    """Map a public RateEntry DTO to an internal ExchangeEdge."""
    return ExchangeEdge(
        source_currency=entry.source_currency,
        target_currency=entry.target_currency,
        rate_value=entry.rate_value,
    )


def _compute_deviation_percent(route_rate: Decimal, best_rate: Decimal) -> Decimal:
    """Compute signed deviation percent from best route rate."""
    return (route_rate - best_rate) / best_rate * Decimal("100")


def _normalize_positive_amount(amount: Decimal) -> Decimal:
    """Return amount when positive or raise validation error."""
    if amount <= Decimal("0"):
        message = "Requested amount must be positive."
        raise NonPositiveAmountError(message)
    return amount


async def _prepare_sorted_paths(
    reader: UserRatesReaderPort,
    user_id: str,
    source_currency: str,
    target_currency: str,
) -> tuple[str, str, tuple[DiscoveredPath, ...]]:
    """Validate inputs, discover paths, and return (source, target, sorted_paths).

    Paths are sorted by effective_rate descending (best first).
    Raises IdenticalCurrencyPairError, NoExchangePathError, or ValueError on invalid input.
    """
    normalized_user_id = normalize_user_id(user_id)
    source = normalize_currency_code(source_currency)
    target = normalize_currency_code(target_currency)

    if source == target:
        message = "Exchange-route currencies must differ."
        raise IdenticalCurrencyPairError(message)

    rate_entries = await reader.list_rates(normalized_user_id)
    edges = [_rate_entry_to_edge(entry) for entry in rate_entries]
    graph = ExchangeGraph.build(edges)
    paths = graph.find_paths(source, target, MAX_EXCHANGES_PER_PATH)

    if not paths:
        message = f"No exchange path from {source} to {target}."
        raise NoExchangePathError(message)

    sorted_paths = tuple(
        sorted(
            paths,
            key=lambda p: p.effective_rate,
            reverse=True,
        )
    )
    return source, target, sorted_paths


class ComputeExchangePathsUseCase:
    """Build all valid exchange paths and rank them by effective rate."""

    def __init__(self, reader: UserRatesReaderPort) -> None:
        """Initialize use case with a user-rates reader port."""
        self._reader = reader

    async def execute(
        self,
        command: ComputeExchangePathsCommand,
    ) -> ComputeExchangePathsResult:
        """Compute ranked routes for user-scoped exchange rates."""
        source, target, sorted_paths = await _prepare_sorted_paths(
            self._reader,
            command.user_id,
            command.source_currency,
            command.target_currency,
        )
        best_rate = sorted_paths[0].effective_rate
        return ComputeExchangePathsResult(
            source_currency=source,
            target_currency=target,
            best_rate=best_rate,
            paths=tuple(
                ExchangePathItem(
                    currencies=path.currencies,
                    effective_rate=path.effective_rate,
                    deviation_percent=_compute_deviation_percent(
                        path.effective_rate, best_rate
                    ),
                )
                for path in sorted_paths
            ),
        )


class ComputeReceivedAmountUseCase:
    """Compute target amounts for all valid routes given source amount."""

    def __init__(self, reader: UserRatesReaderPort) -> None:
        """Initialize use case with a user-rates reader port."""
        self._reader = reader

    async def execute(
        self,
        command: ComputeReceivedAmountCommand,
    ) -> ComputeReceivedAmountResult:
        """Compute received target amount for each route and rank by best outcome."""
        source_amount = _normalize_positive_amount(command.source_amount)
        source, target, sorted_paths = await _prepare_sorted_paths(
            self._reader,
            command.user_id,
            command.source_currency,
            command.target_currency,
        )
        best_target_amount = sorted_paths[0].effective_rate * source_amount
        return ComputeReceivedAmountResult(
            source_currency=source,
            target_currency=target,
            source_amount=source_amount,
            best_target_amount=best_target_amount,
            paths=tuple(
                ExchangeTargetAmountItem(
                    currencies=path.currencies,
                    effective_rate=path.effective_rate,
                    target_amount=path.effective_rate * source_amount,
                    deviation_percent=_compute_deviation_percent(
                        path.effective_rate * source_amount,
                        best_target_amount,
                    ),
                )
                for path in sorted_paths
            ),
        )


class ComputeRequiredSourceAmountUseCase:
    """Compute source amounts needed for all valid routes given target amount."""

    def __init__(self, reader: UserRatesReaderPort) -> None:
        """Initialize use case with a user-rates reader port."""
        self._reader = reader

    async def execute(
        self,
        command: ComputeRequiredSourceAmountCommand,
    ) -> ComputeRequiredSourceAmountResult:
        """Compute required source amount for each route and rank by lowest requirement."""
        target_amount = _normalize_positive_amount(command.target_amount)
        source, target, sorted_paths = await _prepare_sorted_paths(
            self._reader,
            command.user_id,
            command.source_currency,
            command.target_currency,
        )
        # sorted_paths is ordered by effective_rate DESC = source_amount ASC
        # (source_amount = target / rate, so higher rate => lower source_amount => better)
        result_paths_unsorted = tuple(
            RequiredSourceAmountItem(
                currencies=path.currencies,
                effective_rate=path.effective_rate,
                source_amount=target_amount / path.effective_rate,
                deviation_percent=Decimal("0"),
            )
            for path in sorted_paths
        )
        result_paths_sorted = tuple(
            sorted(result_paths_unsorted, key=lambda path: path.source_amount)
        )
        best_source_amount = result_paths_sorted[0].source_amount
        return ComputeRequiredSourceAmountResult(
            source_currency=source,
            target_currency=target,
            target_amount=target_amount,
            best_source_amount=best_source_amount,
            paths=tuple(
                RequiredSourceAmountItem(
                    currencies=path.currencies,
                    effective_rate=path.effective_rate,
                    source_amount=path.source_amount,
                    deviation_percent=_compute_deviation_percent(
                        best_source_amount,
                        path.source_amount,
                    ),
                )
                for path in result_paths_sorted
            ),
        )

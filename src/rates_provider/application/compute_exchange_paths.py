"""Application use case for computing ranked exchange routes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from rates_provider.application._validation import normalize_user_id
from rates_provider.domain.exceptions import (
    IdenticalCurrencyPairError,
    NoExchangePathError,
    NonPositiveAmountError,
)
from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository

MAX_EXCHANGES_PER_PATH = 4


# ── DTOs ──────────────────────────────────────────────────────────────────────


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


# ── Internal ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class _DiscoveredPath:
    """Internal path representation before deviation enrichment."""

    currencies: tuple[str, ...]
    effective_rate: Decimal


# ── Graph ──────────────────────────────────────────────────────────────────────


class ExchangeRateGraph:
    """Directed weighted graph of exchange rates for path discovery."""

    def __init__(self, adjacency: dict[str, list[tuple[str, Decimal]]]) -> None:
        """Initialize graph with a pre-built adjacency list."""
        self._adjacency = adjacency

    @classmethod
    def build(cls, rates: Sequence[ExchangeRate]) -> ExchangeRateGraph:
        """Build graph from exchange rates, keeping the best rate per directional pair."""
        edge_rates: dict[tuple[str, str], Decimal] = {}
        for rate in rates:
            key = (rate.source_currency.value, rate.target_currency.value)
            existing = edge_rates.get(key)
            if existing is None or rate.rate_value > existing:
                edge_rates[key] = rate.rate_value

        adjacency: dict[str, list[tuple[str, Decimal]]] = {}
        for (src, tgt), edge_rate in edge_rates.items():
            adjacency.setdefault(src, []).append((tgt, edge_rate))
        for neighbors in adjacency.values():
            neighbors.sort(key=lambda item: item[0])

        return cls(adjacency)

    def find_paths(
        self,
        source: str,
        target: str,
        max_depth: int,
    ) -> tuple[_DiscoveredPath, ...]:
        """Discover all simple paths from source to target up to max_depth edges."""
        discovered: list[_DiscoveredPath] = []

        def dfs(
            current: str,
            currencies: tuple[str, ...],
            visited: set[str],
            effective_rate: Decimal,
            depth: int,
        ) -> None:
            if current == target and depth > 0:
                discovered.append(
                    _DiscoveredPath(currencies=currencies,
                                    effective_rate=effective_rate)
                )
                return
            if depth >= max_depth:
                return
            for next_currency, next_rate in self._adjacency.get(current, []):
                if next_currency in visited:
                    continue
                dfs(
                    current=next_currency,
                    currencies=currencies + (next_currency,),
                    visited=visited | {next_currency},
                    effective_rate=effective_rate * next_rate,
                    depth=depth + 1,
                )

        dfs(
            current=source,
            currencies=(source,),
            visited={source},
            effective_rate=Decimal("1"),
            depth=0,
        )
        return tuple(discovered)


# ── Shared helpers ─────────────────────────────────────────────────────────────


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
    repository: ExchangeRateRepository,
    user_id: str,
    source_currency: str,
    target_currency: str,
) -> tuple[str, str, tuple[_DiscoveredPath, ...]]:
    """Validate inputs, discover paths, and return (source, target, sorted_paths).

    Paths are sorted by effective_rate descending (best first).
    Raises IdenticalCurrencyPairError, NoExchangePathError, or ValueError on invalid input.
    """
    normalized_user_id = normalize_user_id(user_id)
    source = CurrencyCode(source_currency).value
    target = CurrencyCode(target_currency).value

    if source == target:
        message = "Exchange-route currencies must differ."
        raise IdenticalCurrencyPairError(message)

    rates = await repository.list_all(normalized_user_id)
    graph = ExchangeRateGraph.build(rates)
    paths = graph.find_paths(source, target, MAX_EXCHANGES_PER_PATH)

    if not paths:
        message = f"No exchange path from {source} to {target}."
        raise NoExchangePathError(message)

    sorted_paths = tuple(
        sorted(paths, key=lambda p: p.effective_rate, reverse=True))
    return source, target, sorted_paths


# ── Use cases ──────────────────────────────────────────────────────────────────


class ComputeExchangePathsUseCase:
    """Build all valid exchange paths and rank them by effective rate."""

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize use case with exchange-rate repository."""
        self._repository = repository

    async def execute(
        self,
        command: ComputeExchangePathsCommand,
    ) -> ComputeExchangePathsResult:
        """Compute ranked routes for user-scoped exchange rates."""
        source, target, sorted_paths = await _prepare_sorted_paths(
            self._repository,
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

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize use case with exchange-rate repository."""
        self._repository = repository

    async def execute(
        self,
        command: ComputeReceivedAmountCommand,
    ) -> ComputeReceivedAmountResult:
        """Compute received target amount for each route and rank by best outcome."""
        source_amount = _normalize_positive_amount(command.source_amount)
        source, target, sorted_paths = await _prepare_sorted_paths(
            self._repository,
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

    def __init__(self, repository: ExchangeRateRepository) -> None:
        """Initialize use case with exchange-rate repository."""
        self._repository = repository

    async def execute(
        self,
        command: ComputeRequiredSourceAmountCommand,
    ) -> ComputeRequiredSourceAmountResult:
        """Compute required source amount for each route and rank by lowest requirement."""
        target_amount = _normalize_positive_amount(command.target_amount)
        source, target, sorted_paths = await _prepare_sorted_paths(
            self._repository,
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

"""Directed weighted exchange graph with DFS path discovery."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from .exchange_edge import ExchangeEdge

MAX_EXCHANGES_PER_PATH = 4


@dataclass(frozen=True, slots=True)
class DiscoveredPath:
    """A path found by DFS traversal of the exchange graph."""

    currencies: tuple[str, ...]
    effective_rate: Decimal


class ExchangeGraph:
    """Directed weighted graph of exchange edges for path discovery."""

    def __init__(self, adjacency: dict[str, list[tuple[str, Decimal]]]) -> None:
        """Initialize graph with a pre-built adjacency list."""
        self._adjacency = adjacency

    @classmethod
    def build(cls, edges: Sequence[ExchangeEdge]) -> ExchangeGraph:
        """Build graph from exchange edges, keeping the best rate per directional pair."""
        edge_rates: dict[tuple[str, str], Decimal] = {}
        for edge in edges:
            key = (edge.source_currency, edge.target_currency)
            existing = edge_rates.get(key)
            if existing is None or edge.rate_value > existing:
                edge_rates[key] = edge.rate_value

        adjacency: dict[str, list[tuple[str, Decimal]]] = {}
        for (src, tgt), rate in edge_rates.items():
            adjacency.setdefault(src, []).append((tgt, rate))
        for neighbors in adjacency.values():
            neighbors.sort(key=lambda item: item[0])

        return cls(adjacency)

    def find_paths(
        self,
        source: str,
        target: str,
        max_depth: int,
    ) -> tuple[DiscoveredPath, ...]:
        """Discover all simple paths from source to target up to max_depth edges."""
        discovered: list[DiscoveredPath] = []

        def dfs(
            current: str,
            currencies: tuple[str, ...],
            visited: set[str],
            effective_rate: Decimal,
            depth: int,
        ) -> None:
            if current == target and depth > 0:
                discovered.append(
                    DiscoveredPath(currencies=currencies,
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

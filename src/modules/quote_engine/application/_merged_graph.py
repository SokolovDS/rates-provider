"""Shared helpers for building a merged exchange graph from user and market rates."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared._validation import normalize_currency_code, normalize_user_id
from modules.market_rates.contracts.dtos import MarketRateEntry
from modules.market_rates.contracts.reader_port import MarketRatesReaderPort
from modules.quote_engine.domain.exchange_edge import ExchangeEdge
from modules.quote_engine.domain.graph import ExchangeGraph
from modules.user_rates.contracts.dtos import RateEntry
from modules.user_rates.contracts.reader_port import UserRatesReaderPort


@dataclass(frozen=True, slots=True)
class MergedExchangeGraph:
    """Merged exchange graph and all unique currencies available in it."""

    graph: ExchangeGraph
    currencies: tuple[str, ...]


def rate_entry_to_edge(entry: RateEntry) -> ExchangeEdge:
    """Map a public user rate entry DTO to an internal exchange edge."""
    return ExchangeEdge(
        source_currency=normalize_currency_code(entry.source_currency),
        target_currency=normalize_currency_code(entry.target_currency),
        rate_value=entry.rate_value,
    )


def market_entry_to_edge(entry: MarketRateEntry) -> ExchangeEdge:
    """Map a public market rate entry DTO to an internal exchange edge."""
    return ExchangeEdge(
        source_currency=normalize_currency_code(entry.source_currency),
        target_currency=normalize_currency_code(entry.target_currency),
        rate_value=entry.rate_value,
    )


async def build_merged_exchange_graph(
    user_reader: UserRatesReaderPort,
    market_reader: MarketRatesReaderPort,
    user_id: str,
) -> MergedExchangeGraph:
    """Load user and market rates, normalize them, and build one graph."""
    normalized_user_id = normalize_user_id(user_id)
    user_entries = await user_reader.list_rates(normalized_user_id)
    market_entries = await market_reader.list_rates()
    edges = [
        *(rate_entry_to_edge(entry) for entry in user_entries),
        *(market_entry_to_edge(entry) for entry in market_entries),
    ]
    currencies = tuple(
        sorted(
            {
                currency
                for edge in edges
                for currency in (edge.source_currency, edge.target_currency)
            }
        )
    )
    return MergedExchangeGraph(
        graph=ExchangeGraph.build(edges),
        currencies=currencies,
    )

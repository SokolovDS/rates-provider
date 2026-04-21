"""Read-only use case for listing selectable currencies for exchange-path flows."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared._validation import normalize_currency_code
from modules.market_rates.contracts.reader_port import MarketRatesReaderPort
from modules.quote_engine.application._merged_graph import build_merged_exchange_graph
from modules.quote_engine.domain.graph import MAX_EXCHANGES_PER_PATH
from modules.user_rates.contracts.reader_port import UserRatesReaderPort


@dataclass(frozen=True, slots=True)
class ListSelectableCurrenciesCommand:
    """Input DTO for listing source or target currencies for selection."""

    user_id: str
    source_currency: str | None = None


@dataclass(frozen=True, slots=True)
class ListSelectableCurrenciesResult:
    """Output DTO containing sorted unique currencies for UI selection."""

    currencies: tuple[str, ...]


class ListSelectableCurrenciesUseCase:
    """List source or target currencies from merged user and market rates."""

    def __init__(
        self,
        reader: UserRatesReaderPort,
        market_reader: MarketRatesReaderPort,
    ) -> None:
        """Initialize the use case with user and market rate readers."""
        self._reader = reader
        self._market_reader = market_reader

    async def execute(
        self,
        command: ListSelectableCurrenciesCommand,
    ) -> ListSelectableCurrenciesResult:
        """Return selectable source currencies or reachable targets for a source."""
        merged_graph = await build_merged_exchange_graph(
            self._reader,
            self._market_reader,
            command.user_id,
        )
        if command.source_currency is None:
            return ListSelectableCurrenciesResult(currencies=merged_graph.currencies)

        source_currency = normalize_currency_code(command.source_currency)
        reachable_currencies = tuple(
            currency
            for currency in merged_graph.currencies
            if currency != source_currency
            and merged_graph.graph.find_paths(
                source_currency,
                currency,
                MAX_EXCHANGES_PER_PATH,
            )
        )
        return ListSelectableCurrenciesResult(currencies=reachable_currencies)

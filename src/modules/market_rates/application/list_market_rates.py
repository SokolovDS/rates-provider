"""Application use case for listing all available market exchange rates."""

from dataclasses import dataclass

from modules.market_rates.contracts.dtos import MarketRateEntry
from modules.market_rates.contracts.reader_port import MarketRatesReaderPort


@dataclass(frozen=True, slots=True)
class ListMarketRatesResult:
    """Output DTO describing all available market exchange rates."""

    exchange_rates: tuple[MarketRateEntry, ...]


class ListMarketRatesUseCase:
    """Read and return all available market exchange rates."""

    def __init__(self, reader: MarketRatesReaderPort) -> None:
        """Initialize the use case with a market rates reader."""
        self._reader = reader

    async def execute(self) -> ListMarketRatesResult:
        """Load all market exchange rates and return them as a result DTO."""
        rates = await self._reader.list_rates()
        return ListMarketRatesResult(exchange_rates=tuple(rates))

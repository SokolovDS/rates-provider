"""Public port for reading market-sourced exchange rates."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .dtos import MarketRateEntry


class MarketRatesReaderPort(ABC):
    """Read-only port for fetching global (non-user-scoped) market exchange rates."""

    @abstractmethod
    async def list_rates(self) -> Sequence[MarketRateEntry]:
        """Return all available market exchange-rate records."""

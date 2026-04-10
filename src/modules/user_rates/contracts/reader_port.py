"""Public port for reading user-managed exchange rates."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .dtos import RateEntry


class UserRatesReaderPort(ABC):
    """Read-only port for fetching user-scoped exchange rates."""

    @abstractmethod
    async def list_rates(self, user_id: str) -> Sequence[RateEntry]:
        """Return all active exchange-rate records for the given user."""

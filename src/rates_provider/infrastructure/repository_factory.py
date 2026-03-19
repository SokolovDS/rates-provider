"""Factory helpers for infrastructure repository wiring."""

from rates_provider.config import load_sqlite_db_path, load_storage_backend
from rates_provider.domain.repositories import ExchangeRateRepository
from rates_provider.infrastructure.memory_exchange_rate_repository import (
    InMemoryExchangeRateRepository,
)
from rates_provider.infrastructure.sqlite_exchange_rate_repository import (
    SQLiteExchangeRateRepository,
)


def build_exchange_rate_repository() -> ExchangeRateRepository:
    """Build exchange-rate repository according to runtime configuration."""
    backend_name = load_storage_backend()
    if backend_name == "memory":
        return InMemoryExchangeRateRepository()

    sqlite_db_path = load_sqlite_db_path()
    return SQLiteExchangeRateRepository(sqlite_db_path)

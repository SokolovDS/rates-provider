"""Infrastructure wiring — sole composition point for all module repositories."""

from app.bootstrap.config import (
    load_rates_sqlite_db_path,
    load_storage_backend,
    load_users_sqlite_db_path,
)
from modules.identity.domain.repositories import UserRepository
from modules.identity.infrastructure.memory_user_repository import InMemoryUserRepository
from modules.identity.infrastructure.sqlite_user_repository import SQLiteUserRepository
from modules.user_rates.domain.repositories import ExchangeRateRepository
from modules.user_rates.infrastructure.memory_exchange_rate_repository import (
    InMemoryExchangeRateRepository,
)
from modules.user_rates.infrastructure.sqlite_exchange_rate_repository import (
    SQLiteExchangeRateRepository,
)


def build_exchange_rate_repository() -> ExchangeRateRepository:
    """Build exchange-rate repository according to runtime configuration."""
    backend_name = load_storage_backend()
    if backend_name == "memory":
        return InMemoryExchangeRateRepository()

    sqlite_db_path = load_rates_sqlite_db_path()
    return SQLiteExchangeRateRepository(sqlite_db_path)


def build_user_repository() -> UserRepository:
    """Build user repository according to runtime configuration."""
    backend_name = load_storage_backend()
    if backend_name == "memory":
        return InMemoryUserRepository()

    sqlite_db_path = load_users_sqlite_db_path()
    return SQLiteUserRepository(sqlite_db_path)

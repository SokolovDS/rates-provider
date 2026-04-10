"""Configuration loading for application runtime."""

import os
from typing import Literal, cast

from dotenv import load_dotenv


def _load_environment() -> None:
    """Load environment variables from .env if present."""
    load_dotenv()


def load_bot_token(env_var_name: str = "TELEGRAM_BOT_TOKEN") -> str:
    """Load the Telegram bot token from environment variables."""
    _load_environment()
    token = os.getenv(env_var_name)
    if token is None or token.strip() == "":
        error_message = f"Environment variable {env_var_name} is required"
        raise RuntimeError(error_message)
    return token


def load_sqlite_db_path(
    env_var_name: str = "SQLITE_DB_PATH",
    default_path: str = "data/exchange_rates.sqlite3",
) -> str:
    """Load SQLite database file path from environment variables."""
    _load_environment()
    database_path = os.getenv(env_var_name, default_path).strip()
    if database_path == "":
        error_message = f"Environment variable {env_var_name} must not be empty"
        raise RuntimeError(error_message)
    return database_path


def load_rates_sqlite_db_path(
    env_var_name: str = "SQLITE_RATES_DB_PATH",
    default_path: str = "data/exchange_rates.sqlite3",
) -> str:
    """Load SQLite database path for exchange-rate persistence."""
    return load_sqlite_db_path(env_var_name=env_var_name, default_path=default_path)


def load_users_sqlite_db_path(
    env_var_name: str = "SQLITE_USERS_DB_PATH",
    default_path: str = "data/users_service.sqlite3",
) -> str:
    """Load SQLite database path for user persistence."""
    return load_sqlite_db_path(env_var_name=env_var_name, default_path=default_path)


def load_storage_backend(
    env_var_name: str = "STORAGE_BACKEND",
    default_backend: str = "sqlite",
) -> Literal["sqlite", "memory"]:
    """Load and validate configured repository backend name."""
    _load_environment()
    backend_name = os.getenv(env_var_name, default_backend).strip().lower()
    if backend_name not in {"sqlite", "memory"}:
        error_message = (
            f"Invalid storage backend '{backend_name}'. Must be 'sqlite' or 'memory'."
        )
        raise RuntimeError(error_message)
    return cast(Literal["sqlite", "memory"], backend_name)

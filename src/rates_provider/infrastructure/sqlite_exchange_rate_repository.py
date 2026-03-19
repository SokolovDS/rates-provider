"""SQLite-backed exchange-rate repository implementation."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class SQLiteExchangeRateRepository(ExchangeRateRepository):
    """Append-only SQLite storage for exchange-rate history."""

    def __init__(self, database_path: str) -> None:
        """Initialize repository and ensure schema exists."""
        self._database_path: Path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Append a new exchange-rate record to SQLite storage."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO exchange_rates (
                    user_id,
                    source_currency,
                    target_currency,
                    rate_value,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    exchange_rate.source_currency.value,
                    exchange_rate.target_currency.value,
                    str(exchange_rate.rate_value),
                    exchange_rate.created_at.isoformat(),
                ),
            )
            connection.commit()

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return stored exchange-rate records for a specific user."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT user_id, source_currency, target_currency, rate_value, created_at
                FROM exchange_rates
                WHERE user_id = ?
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
        return tuple(self._row_to_exchange_rate(row) for row in rows)

    def _initialize_schema(self) -> None:
        """Create required SQLite tables if they do not already exist."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    source_currency TEXT NOT NULL,
                    target_currency TEXT NOT NULL,
                    rate_value TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_user_id_column(connection)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_exchange_rates_user_id
                ON exchange_rates(user_id)
                """
            )
            connection.commit()

    def _ensure_user_id_column(self, connection: sqlite3.Connection) -> None:
        """Ensure legacy schemas contain user_id required for per-user isolation."""
        table_columns = connection.execute(
            "PRAGMA table_info(exchange_rates)"
        ).fetchall()
        column_names = {cast(str, row["name"]) for row in table_columns}
        if "user_id" in column_names:
            return
        connection.execute(
            "ALTER TABLE exchange_rates ADD COLUMN user_id TEXT NOT NULL DEFAULT ''"
        )

    def _connect(self) -> sqlite3.Connection:
        """Open SQLite connection configured for named-column access."""
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_exchange_rate(self, row: sqlite3.Row) -> ExchangeRate:
        """Map database row data into a validated domain entity."""
        source_currency = CurrencyCode(cast(str, row["source_currency"]))
        target_currency = CurrencyCode(cast(str, row["target_currency"]))
        rate_value = Decimal(cast(str, row["rate_value"]))
        created_at = datetime.fromisoformat(cast(str, row["created_at"]))
        return ExchangeRate(
            source_currency=source_currency,
            target_currency=target_currency,
            rate_value=rate_value,
            created_at=created_at,
        )

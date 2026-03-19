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

    async def add(self, exchange_rate: ExchangeRate) -> None:
        """Append a new exchange-rate record to SQLite storage."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO exchange_rates (
                    source_currency,
                    target_currency,
                    rate_value,
                    created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    exchange_rate.source_currency.value,
                    exchange_rate.target_currency.value,
                    str(exchange_rate.rate_value),
                    exchange_rate.created_at.isoformat(),
                ),
            )
            connection.commit()

    async def list_all(self) -> Sequence[ExchangeRate]:
        """Return all stored exchange-rate records in insertion order."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_currency, target_currency, rate_value, created_at
                FROM exchange_rates
                ORDER BY id ASC
                """
            ).fetchall()
        return tuple(self._row_to_exchange_rate(row) for row in rows)

    def _initialize_schema(self) -> None:
        """Create required SQLite tables if they do not already exist."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_currency TEXT NOT NULL,
                    target_currency TEXT NOT NULL,
                    rate_value TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

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

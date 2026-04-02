"""SQLite-backed exchange-rate repository implementation."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class SQLiteExchangeRateRepository(ExchangeRateRepository):
    """Latest-only SQLite storage with soft deletion per currency pair."""

    def __init__(self, database_path: str) -> None:
        """Initialize repository and ensure schema exists."""
        self._database_path: Path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Upsert a user-scoped active exchange-rate record in SQLite storage."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO exchange_rates (
                    user_id,
                    source_currency,
                    target_currency,
                    rate_value,
                    created_at,
                    deleted_at
                ) VALUES (?, ?, ?, ?, ?, NULL)
                ON CONFLICT(user_id, source_currency, target_currency)
                DO UPDATE SET
                    rate_value = excluded.rate_value,
                    created_at = excluded.created_at,
                    deleted_at = NULL
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

    async def update(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Update an existing active exchange-rate record in SQLite storage."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE exchange_rates
                SET rate_value = ?,
                    created_at = ?,
                    deleted_at = NULL
                WHERE user_id = ?
                  AND source_currency = ?
                  AND target_currency = ?
                  AND deleted_at IS NULL
                """,
                (
                    str(exchange_rate.rate_value),
                    exchange_rate.created_at.isoformat(),
                    user_id,
                    exchange_rate.source_currency.value,
                    exchange_rate.target_currency.value,
                ),
            )
            if cursor.rowcount == 0:
                source = exchange_rate.source_currency.value
                target = exchange_rate.target_currency.value
                raise ValueError(
                    f"Exchange rate {source}->{target} does not exist.")
            connection.commit()

    async def delete(
        self,
        user_id: str,
        source_currency: CurrencyCode,
        target_currency: CurrencyCode,
    ) -> None:
        """Soft-delete an active exchange-rate record for the provided pair."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE exchange_rates
                SET deleted_at = ?
                WHERE user_id = ?
                  AND source_currency = ?
                  AND target_currency = ?
                  AND deleted_at IS NULL
                """,
                (
                    datetime.now(tz=UTC).isoformat(),
                    user_id,
                    source_currency.value,
                    target_currency.value,
                ),
            )
            if cursor.rowcount == 0:
                pair_name = f"{source_currency.value}->{target_currency.value}"
                raise ValueError(
                    f"Exchange rate {pair_name} does not exist."
                )
            connection.commit()

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return active latest exchange-rate records for a specific user."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT user_id, source_currency, target_currency, rate_value, created_at
                FROM exchange_rates
                WHERE user_id = ?
                  AND deleted_at IS NULL
                ORDER BY source_currency ASC, target_currency ASC
                """,
                (user_id,),
            ).fetchall()
        return tuple(self._row_to_exchange_rate(row) for row in rows)

    def _initialize_schema(self) -> None:
        """Create required SQLite tables if they do not already exist."""
        with self._connect() as connection:
            if not self._table_exists(connection, "exchange_rates"):
                self._create_latest_only_table(connection)
                self._create_indexes(connection)
                connection.commit()
                return

            self._ensure_user_id_column(connection)
            if not self._has_column(connection, "exchange_rates", "deleted_at"):
                self._migrate_history_table_to_latest_only(connection)

            self._create_indexes(connection)
            connection.commit()

    def _migrate_history_table_to_latest_only(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        """Convert historical append-only schema into latest-only schema."""
        connection.execute(
            "ALTER TABLE exchange_rates RENAME TO exchange_rates_legacy")
        self._create_latest_only_table(connection)

        connection.execute(
            """
            INSERT INTO exchange_rates (
                user_id,
                source_currency,
                target_currency,
                rate_value,
                created_at,
                deleted_at
            )
            SELECT
                legacy.user_id,
                legacy.source_currency,
                legacy.target_currency,
                legacy.rate_value,
                legacy.created_at,
                NULL
            FROM exchange_rates_legacy AS legacy
            WHERE legacy.id = (
                SELECT MAX(candidate.id)
                FROM exchange_rates_legacy AS candidate
                WHERE candidate.user_id = legacy.user_id
                  AND candidate.source_currency = legacy.source_currency
                  AND candidate.target_currency = legacy.target_currency
            )
            """
        )
        connection.execute("DROP TABLE exchange_rates_legacy")

    def _create_latest_only_table(self, connection: sqlite3.Connection) -> None:
        """Create latest-only exchange-rate table with pair uniqueness."""
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                source_currency TEXT NOT NULL,
                target_currency TEXT NOT NULL,
                rate_value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                UNIQUE(user_id, source_currency, target_currency)
            )
            """
        )

    def _create_indexes(self, connection: sqlite3.Connection) -> None:
        """Create indexes needed for latest-only lookups and filtering."""
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_exchange_rates_user_id
            ON exchange_rates(user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_exchange_rates_active_pairs
            ON exchange_rates(user_id, source_currency, target_currency, deleted_at)
            """
        )

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

    def _table_exists(self, connection: sqlite3.Connection, table_name: str) -> bool:
        """Return True when table exists in current SQLite database."""
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        ).fetchone()
        return row is not None

    def _has_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
    ) -> bool:
        """Return True when given table contains requested column."""
        if table_name != "exchange_rates":
            msg = f"Unexpected table name for schema inspection: {table_name!r}"
            raise ValueError(msg)
        table_columns = connection.execute(
            "PRAGMA table_info(exchange_rates)"
        ).fetchall()
        column_names = {cast(str, row["name"]) for row in table_columns}
        return column_name in column_names

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

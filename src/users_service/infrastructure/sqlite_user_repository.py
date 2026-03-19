"""SQLite implementation of user repository with external identity mapping."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from users_service.domain.repositories import UserRepository
from users_service.domain.user import ExternalIdentity, User, UserId, UserStatus


class SQLiteUserRepository(UserRepository):
    """Persist users and provider identities in SQLite."""

    def __init__(self, database_path: str) -> None:
        """Initialize repository and create schema when missing."""
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    async def get_or_create_by_external_identity(self, identity: ExternalIdentity) -> User:
        """Return user by external identity, creating account atomically if absent."""
        with self._connect() as connection:
            existing_user = self._find_user(connection, identity)
            if existing_user is not None:
                return self._touch_last_seen(connection, existing_user)

            created_user = self._insert_user_with_identity(
                connection, identity)
            return created_user

    def _initialize_schema(self) -> None:
        """Create users and external identities tables if they do not exist."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_external_identities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_subject TEXT NOT NULL,
                    provider_username TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, provider_subject),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_external_identities_user_id
                ON user_external_identities(user_id)
                """
            )
            connection.commit()

    def _find_user(
        self,
        connection: sqlite3.Connection,
        identity: ExternalIdentity,
    ) -> User | None:
        """Load user by external identity mapping."""
        row = connection.execute(
            """
            SELECT u.id, u.status, u.created_at, u.updated_at, u.last_seen_at
            FROM users u
            JOIN user_external_identities e ON e.user_id = u.id
            WHERE e.provider = ? AND e.provider_subject = ?
            """,
            (identity.provider.value, identity.subject),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def _touch_last_seen(self, connection: sqlite3.Connection, user: User) -> User:
        """Update user's activity timestamp and return refreshed object."""
        timestamp = datetime.now(UTC)
        timestamp_raw = timestamp.isoformat()
        connection.execute(
            """
            UPDATE users
            SET updated_at = ?, last_seen_at = ?
            WHERE id = ?
            """,
            (timestamp_raw, timestamp_raw, user.user_id.value),
        )
        connection.commit()
        return User(
            user_id=user.user_id,
            status=user.status,
            created_at=user.created_at,
            updated_at=timestamp,
            last_seen_at=timestamp,
        )

    def _insert_user_with_identity(
        self,
        connection: sqlite3.Connection,
        identity: ExternalIdentity,
    ) -> User:
        """Insert new user and external identity relation with race-safe fallback."""
        timestamp = datetime.now(UTC)
        timestamp_raw = timestamp.isoformat()
        new_user_id = str(uuid4())

        try:
            connection.execute(
                """
                INSERT INTO users (id, status, created_at, updated_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (new_user_id, UserStatus.ACTIVE.value,
                 timestamp_raw, timestamp_raw, timestamp_raw),
            )
            connection.execute(
                """
                INSERT INTO user_external_identities (
                    user_id,
                    provider,
                    provider_subject,
                    provider_username,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_user_id,
                    identity.provider.value,
                    identity.subject,
                    identity.username,
                    timestamp_raw,
                    timestamp_raw,
                ),
            )
            connection.commit()
            return User(
                user_id=UserId(new_user_id),
                status=UserStatus.ACTIVE,
                created_at=timestamp,
                updated_at=timestamp,
                last_seen_at=timestamp,
            )
        except sqlite3.IntegrityError as error:
            connection.rollback()
            existing_user = self._find_user(connection, identity)
            if existing_user is None:
                message = "Failed to create or load user after identity conflict."
                raise RuntimeError(message) from error
            return self._touch_last_seen(connection, existing_user)

    def _connect(self) -> sqlite3.Connection:
        """Open SQLite connection configured for row access by column name."""
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Map SQLite row into user domain entity."""
        return User(
            user_id=UserId(cast(str, row["id"])),
            status=UserStatus(cast(str, row["status"])),
            created_at=datetime.fromisoformat(cast(str, row["created_at"])),
            updated_at=datetime.fromisoformat(cast(str, row["updated_at"])),
            last_seen_at=datetime.fromisoformat(
                cast(str, row["last_seen_at"])),
        )

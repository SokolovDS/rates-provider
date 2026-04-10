"""In-memory implementation of user repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from modules.identity.domain.repositories import UserRepository
from modules.identity.domain.user import ExternalIdentity, User, UserId, UserStatus


class InMemoryUserRepository(UserRepository):
    """Store users and external identities in in-memory dictionaries."""

    def __init__(self) -> None:
        """Initialize empty in-memory user storage."""
        self._users: dict[str, User] = {}
        self._external_identity_to_user_id: dict[tuple[str, str], str] = {}

    async def get_or_create_by_external_identity(self, identity: ExternalIdentity) -> User:
        """Return existing user by identity or create a fresh active user."""
        identity_key = (identity.provider.value, identity.subject)
        existing_user_id = self._external_identity_to_user_id.get(identity_key)
        if existing_user_id is not None:
            existing_user = self._users[existing_user_id]
            timestamp = datetime.now(UTC)
            updated_user = User(
                user_id=existing_user.user_id,
                status=existing_user.status,
                created_at=existing_user.created_at,
                updated_at=timestamp,
                last_seen_at=timestamp,
            )
            self._users[existing_user_id] = updated_user
            return updated_user

        new_user_id = str(uuid4())
        timestamp = datetime.now(UTC)
        user = User(
            user_id=UserId(new_user_id),
            status=UserStatus.ACTIVE,
            created_at=timestamp,
            updated_at=timestamp,
            last_seen_at=timestamp,
        )
        self._users[new_user_id] = user
        self._external_identity_to_user_id[identity_key] = new_user_id
        return user

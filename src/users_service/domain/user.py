"""Domain entities and value objects for the user service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ExternalIdentityProvider(StrEnum):
    """Supported external identity providers."""

    TELEGRAM = "telegram"


class UserStatus(StrEnum):
    """Lifecycle status of a user account."""

    ACTIVE = "active"


@dataclass(frozen=True, slots=True)
class UserId:
    """Stable internal user identifier represented as UUID string."""

    value: str

    def __post_init__(self) -> None:
        """Validate that user identifier is a non-empty UUID string."""
        normalized_value = self.value.strip()
        UUID(normalized_value)
        object.__setattr__(self, "value", normalized_value)


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    """External identity bound to an internal user account."""

    provider: ExternalIdentityProvider
    subject: str
    username: str | None = None

    def __post_init__(self) -> None:
        """Normalize subject and optional username fields."""
        normalized_subject = self.subject.strip()
        if normalized_subject == "":
            message = "External identity subject must not be empty."
            raise ValueError(message)

        if self.username is None:
            normalized_username: str | None = None
        else:
            stripped_username = self.username.strip()
            normalized_username = stripped_username or None

        object.__setattr__(self, "subject", normalized_subject)
        object.__setattr__(self, "username", normalized_username)


@dataclass(frozen=True, slots=True)
class User:
    """User aggregate root with timestamps and lifecycle status."""

    user_id: UserId
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

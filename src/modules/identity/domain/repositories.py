"""Repository ports for identity module storage."""

from abc import ABC, abstractmethod

from .user import ExternalIdentity, User


class UserRepository(ABC):
    """Port describing persistent user storage and identity mapping."""

    @abstractmethod
    async def get_or_create_by_external_identity(self, identity: ExternalIdentity) -> User:
        """Load existing user by external identity or create a new user."""

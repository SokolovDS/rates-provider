"""Application use case for Telegram user bootstrap in User Service."""

from dataclasses import dataclass

from users_service.domain.repositories import UserRepository
from users_service.domain.user import ExternalIdentity, ExternalIdentityProvider, User


@dataclass(frozen=True, slots=True)
class ResolveOrCreateTelegramUserCommand:
    """Input DTO for resolving or creating a Telegram-backed user."""

    telegram_user_id: int
    username: str | None = None


class ResolveOrCreateTelegramUserUseCase:
    """Resolve internal user for Telegram identity, creating it when missing."""

    def __init__(self, user_repository: UserRepository) -> None:
        """Initialize use case with user repository port."""
        self._user_repository = user_repository

    async def execute(self, command: ResolveOrCreateTelegramUserCommand) -> User:
        """Return existing user or create a new one for Telegram identity."""
        identity = ExternalIdentity(
            provider=ExternalIdentityProvider.TELEGRAM,
            subject=str(command.telegram_user_id),
            username=command.username,
        )
        return await self._user_repository.get_or_create_by_external_identity(identity)

"""Scene for editing active exchange-rate values in Telegram bot UI."""

from decimal import InvalidOperation
from typing import ClassVar

from aiogram.fsm.scene import on
from aiogram.types import Message

from rates_provider.application.update_exchange_rate import (
    UpdateExchangeRateCommand,
    UpdateExchangeRateUseCase,
)
from rates_provider.domain.exceptions import (
    DomainValidationError,
    NonPositiveRateValueError,
)
from users_service.domain.user import User as InternalUser

from ..base import BaseTelegramScene, handle_exceptions
from ..shared.formatting import format_rate_value_plain, parse_rate_value
from ..shared.state_keys import (
    EDIT_RATE_SOURCE_CURRENCY_KEY,
    EDIT_RATE_TARGET_CURRENCY_KEY,
)


def edit_error_message(error: Exception) -> str:
    """Map edit validation errors to user-friendly Russian text."""
    if isinstance(error, (InvalidOperation, NonPositiveRateValueError)):
        return "Ошибка: курс должен быть положительным числом, например 90.50."
    if isinstance(error, DomainValidationError):
        return "Ошибка: не удалось изменить курс. Проверьте введенные данные."
    if isinstance(error, ValueError):
        return "Ошибка: выбранная валютная пара не найдена."
    return "Ошибка: не удалось изменить курс."


class EditRateValueScene(BaseTelegramScene, state="edit_rate:value"):
    """Scene that updates rate value for previously selected currency pair."""

    _PROMPT_TEXT: ClassVar[str] = "Введи новый курс (например 90.50)."

    async def _create_base_lines(self) -> list[str]:
        """Build prompt lines with selected currency pair context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(EDIT_RATE_SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(EDIT_RATE_TARGET_CURRENCY_KEY, "-"))
        return [
            "Изменение курса",
            f"Пара: {source_currency} -> {target_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(edit_error_message, InvalidOperation, DomainValidationError, ValueError)
    async def on_new_rate_value(
        self,
        message: Message,
        update_exchange_rate_use_case: UpdateExchangeRateUseCase,
        current_user: InternalUser,
    ) -> None:
        """Validate user input and update exchange rate for selected pair."""
        await self._best_effort_delete_user_message(message)
        rate_value = parse_rate_value(message.text or "")

        data = await self.wizard.get_data()
        source_currency = str(data.get(EDIT_RATE_SOURCE_CURRENCY_KEY, ""))
        target_currency = str(data.get(EDIT_RATE_TARGET_CURRENCY_KEY, ""))

        result = await update_exchange_rate_use_case.execute(
            UpdateExchangeRateCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
                target_currency=target_currency,
                rate_value=rate_value,
            )
        )

        confirmation_text = (
            "Курс обновлен:\n"
            f"{result.source_currency} -> {result.target_currency} = "
            f"{format_rate_value_plain(result.rate_value)}"
        )
        await self._render_for_message(message, confirmation_text, None)
        await self.collapse_to("rates_list", fresh_ui_message=True)

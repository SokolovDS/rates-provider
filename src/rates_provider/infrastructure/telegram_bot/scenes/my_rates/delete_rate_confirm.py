"""Scene for confirming soft deletion of active exchange rates."""

from typing import ClassVar

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from rates_provider.application.delete_exchange_rate import (
    DeleteExchangeRateCommand,
    DeleteExchangeRateUseCase,
)
from users_service.domain.user import User as InternalUser

from ..base import BaseTelegramScene
from ..shared.state_keys import (
    DELETE_RATE_SOURCE_CURRENCY_KEY,
    DELETE_RATE_TARGET_CURRENCY_KEY,
)


def _build_delete_success_text(source_currency: str, target_currency: str) -> str:
    """Build user-facing confirmation text after successful deletion."""
    return (
        "Курс удален:\n"
        f"{source_currency} -> {target_currency}"
    )


class DeleteRateConfirmScene(BaseTelegramScene, state="delete_rate:confirm"):
    """Scene that asks user to confirm soft deletion for selected pair."""

    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(
            text="Удалить", callback_data="confirm_delete_rate")
    ]

    async def _create_base_lines(self) -> list[str]:
        """Build confirmation prompt with selected pair context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(DELETE_RATE_SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(DELETE_RATE_TARGET_CURRENCY_KEY, "-"))
        return [
            "Удаление курса",
            f"Пара: {source_currency} -> {target_currency}",
            "",
            "Подтверди удаление курса.",
        ]

    @on.callback_query(F.data == "confirm_delete_rate")
    async def on_confirm_delete(
        self,
        callback_query: CallbackQuery,
        delete_exchange_rate_use_case: DeleteExchangeRateUseCase,
        current_user: InternalUser,
    ) -> None:
        """Delete selected pair and return to active rates list scene."""
        await callback_query.answer()
        data = await self.wizard.get_data()
        source_currency = str(data.get(DELETE_RATE_SOURCE_CURRENCY_KEY, ""))
        target_currency = str(data.get(DELETE_RATE_TARGET_CURRENCY_KEY, ""))

        await delete_exchange_rate_use_case.execute(
            DeleteExchangeRateCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
                target_currency=target_currency,
            )
        )

        message = callback_query.message
        if isinstance(message, Message):
            confirmation_text = _build_delete_success_text(
                source_currency,
                target_currency,
            )
            await self._render_for_message(message, confirmation_text, None)

        await self.collapse_to("rates_list", fresh_ui_message=True)

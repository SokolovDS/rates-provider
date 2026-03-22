"""Scene for displaying stored exchange rates in Telegram bot UI."""

from datetime import UTC, datetime
from decimal import Decimal

from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from rates_provider.application.list_exchange_rates import (
    ListExchangeRatesResult,
    ListExchangeRatesUseCase,
)
from users_service.domain.user import User as InternalUser

from .base import BaseTelegramScene


def _format_rate_value(rate_value: Decimal) -> str:
    """Format Decimal rate without scientific notation."""
    return format(rate_value, "f")


def _format_created_at(created_at: datetime) -> str:
    """Format timestamp in a compact UTC representation for Telegram UI."""
    utc_timestamp = created_at.astimezone(UTC)
    return utc_timestamp.strftime("%Y.%m.%d %H:%M:%S UTC")


def _build_list_rates_lines(result: ListExchangeRatesResult) -> list[str]:
    """Build user-facing text lines for the stored exchange-rate list."""
    if not result.exchange_rates:
        return ["Курсы обмена", "", "Курсы пока не добавлены."]

    lines = ["Курсы обмена", ""]
    for item in reversed(result.exchange_rates):
        lines.append(
            f"{item.source_currency} -> {item.target_currency} = "
            f"{_format_rate_value(item.rate_value)} "
            f"({_format_created_at(item.created_at)})"
        )
    return lines


class ListRatesScene(BaseTelegramScene, state="rates_list"):
    """Scene that shows the stored exchange-rate history."""

    async def _list_payload(
        self,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup for the stored exchange-rate list."""
        result = await list_exchange_rates_use_case.execute(current_user.user_id.value)
        text = "\n".join(_build_list_rates_lines(result))
        return text, await self.reply_markup()

    @on.message.enter()
    async def on_enter_from_message(
        self,
        message: Message,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> None:
        """Send list message when entered from a message event."""
        text, reply_markup = await self._list_payload(
            list_exchange_rates_use_case,
            current_user,
        )
        ui_message = await message.answer(text, reply_markup=reply_markup)
        await self.wizard.update_data({self._UI_MESSAGE_ID_KEY: ui_message.message_id})

    @on.callback_query.enter()
    async def on_enter_from_callback(
        self,
        callback_query: CallbackQuery,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> None:
        """Edit existing UI shell when list scene is opened from callback."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._list_payload(
            list_exchange_rates_use_case,
            current_user,
        )
        await message.edit_text(text, reply_markup=reply_markup)
        await self.wizard.update_data({self._UI_MESSAGE_ID_KEY: message.message_id})

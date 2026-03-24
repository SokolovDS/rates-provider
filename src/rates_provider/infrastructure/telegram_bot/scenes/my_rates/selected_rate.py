"""Scene for showing selected exchange-rate pair actions in Telegram bot UI."""

from typing import ClassVar

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from rates_provider.application.list_exchange_rates import (
    ListExchangeRatesResult,
    ListExchangeRatesUseCase,
)
from users_service.domain.user import User as InternalUser

from ..base import BaseTelegramScene
from ..shared.formatting import format_created_at_utc, format_rate_value_plain
from ..shared.state_keys import (
    DELETE_RATE_SOURCE_CURRENCY_KEY,
    DELETE_RATE_TARGET_CURRENCY_KEY,
    EDIT_RATE_SOURCE_CURRENCY_KEY,
    EDIT_RATE_TARGET_CURRENCY_KEY,
    SELECTED_RATE_SOURCE_CURRENCY_KEY,
    SELECTED_RATE_TARGET_CURRENCY_KEY,
)
from .delete_rate_confirm import DeleteRateConfirmScene
from .edit_rate import EditRateValueScene

EDIT_SELECTED_RATE_CALLBACK_DATA = "selected_rate_edit"
DELETE_SELECTED_RATE_CALLBACK_DATA = "selected_rate_delete"


class SelectedRateScene(BaseTelegramScene, state="rates_selected"):
    """Scene that renders selected pair details and edit/delete actions."""

    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(
            text="Изменить", callback_data=EDIT_SELECTED_RATE_CALLBACK_DATA),
        InlineKeyboardButton(
            text="Удалить", callback_data=DELETE_SELECTED_RATE_CALLBACK_DATA),
    ]

    async def _selected_payload(
        self,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup for selected pair details and actions."""
        source_currency, target_currency = await self._selected_pair()
        result = await list_exchange_rates_use_case.execute(current_user.user_id.value)
        text = "\n".join(
            _build_selected_pair_lines(
                result, source_currency, target_currency)
        )
        return text, await self.reply_markup()

    async def _selected_pair(self) -> tuple[str, str]:
        """Read selected pair values from current scene data."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SELECTED_RATE_SOURCE_CURRENCY_KEY, ""))
        target_currency = str(data.get(SELECTED_RATE_TARGET_CURRENCY_KEY, ""))
        return source_currency, target_currency

    @on.message.enter()
    async def on_enter_from_message(
        self,
        message: Message,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> None:
        """Render selected-pair action screen when entered from message."""
        text, reply_markup = await self._selected_payload(
            list_exchange_rates_use_case,
            current_user,
        )
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(
        self,
        callback_query: CallbackQuery,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> None:
        """Render selected-pair action screen when entered from callback."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return

        text, reply_markup = await self._selected_payload(
            list_exchange_rates_use_case,
            current_user,
        )
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query(F.data == EDIT_SELECTED_RATE_CALLBACK_DATA)
    async def on_edit_click(self, callback_query: CallbackQuery) -> None:
        """Open edit-rate scene for currently selected pair."""
        await callback_query.answer()
        source_currency, target_currency = await self._selected_pair()
        await self.wizard.update_data(
            {
                EDIT_RATE_SOURCE_CURRENCY_KEY: source_currency,
                EDIT_RATE_TARGET_CURRENCY_KEY: target_currency,
            }
        )
        await self.wizard.goto(EditRateValueScene)

    @on.callback_query(F.data == DELETE_SELECTED_RATE_CALLBACK_DATA)
    async def on_delete_click(self, callback_query: CallbackQuery) -> None:
        """Open delete-confirm scene for currently selected pair."""
        await callback_query.answer()
        source_currency, target_currency = await self._selected_pair()
        await self.wizard.update_data(
            {
                DELETE_RATE_SOURCE_CURRENCY_KEY: source_currency,
                DELETE_RATE_TARGET_CURRENCY_KEY: target_currency,
            }
        )
        await self.wizard.goto(DeleteRateConfirmScene)


def _build_selected_pair_lines(
    result: ListExchangeRatesResult,
    source_currency: str,
    target_currency: str,
) -> list[str]:
    """Build user-facing text lines for selected pair action menu state."""
    selected_item = next(
        (
            item
            for item in result.exchange_rates
            if item.source_currency == source_currency
            and item.target_currency == target_currency
        ),
        None,
    )
    if selected_item is None:
        return ["Курсы обмена", "", "Выбранная валютная пара не найдена."]

    return [
        "Курсы обмена",
        f"Пара: {selected_item.source_currency} -> {selected_item.target_currency}",
        (
            "Текущий курс: "
            f"{format_rate_value_plain(selected_item.rate_value)} "
            f"({format_created_at_utc(selected_item.created_at)})"
        ),
        "",
        "Выбери действие:",
    ]

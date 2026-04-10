"""Scene for showing selected exchange-rate pair actions in Telegram bot UI."""

from typing import Any, ClassVar, cast

from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from interfaces.telegram_bot.callbacks.my_rates import (
    SelectedRateDeleteCallback,
    SelectedRateEditCallback,
)
from modules.identity.domain.user import User as InternalUser
from modules.user_rates.application.list_exchange_rates import (
    ListExchangeRatesResult,
    ListExchangeRatesUseCase,
)

from ..base import BaseTelegramScene
from ..shared.formatting import format_created_at_utc, format_rate_value_plain
from ..shared.state_keys import SOURCE_CURRENCY_KEY, TARGET_CURRENCY_KEY
from .delete_rate_confirm import DeleteRateConfirmScene
from .edit_rate import EditRateValueScene


class SelectedRateScene(BaseTelegramScene, state="rates_selected"):
    """Scene that renders selected pair details and edit/delete actions."""

    _TEXT_LINES: ClassVar[list[str]] = ["Курсы обмена"]
    _PROMPT_TEXT: ClassVar[str] = "Выбери действие:"
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(
            text="Изменить", callback_data=SelectedRateEditCallback().pack()),
        InlineKeyboardButton(
            text="Удалить", callback_data=SelectedRateDeleteCallback().pack()),
    ]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup for selected pair details and actions."""
        list_exchange_rates_use_case = cast(
            ListExchangeRatesUseCase,
            kwargs["list_exchange_rates_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        source_currency, target_currency = await self._selected_pair()
        result = await list_exchange_rates_use_case.execute(current_user.user_id.value)
        pair_lines = _build_selected_pair_lines(
            result,
            source_currency,
            target_currency,
        )
        text = "\n".join(
            [*self._TEXT_LINES, "", *pair_lines, "", self._PROMPT_TEXT]
        )
        rows = self._configured_rows()
        return text, await self._build_markup(rows)

    async def _selected_pair(self) -> tuple[str, str]:
        """Read selected pair values from current scene data."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, ""))
        return source_currency, target_currency

    @on.callback_query(SelectedRateEditCallback.filter())
    async def on_edit_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Open edit-rate scene for currently selected pair."""
        await callback_query.answer()
        await self.wizard.goto(EditRateValueScene)

    @on.callback_query(SelectedRateDeleteCallback.filter())
    async def on_delete_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Open delete-confirm scene for currently selected pair."""
        await callback_query.answer()
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
        return ["Выбранная валютная пара не найдена."]

    return [
        f"Пара: {selected_item.source_currency} -> {selected_item.target_currency}",
        (
            "Текущий курс: "
            f"{format_rate_value_plain(selected_item.rate_value)} "
            f"({format_created_at_utc(selected_item.created_at)})"
        ),
    ]

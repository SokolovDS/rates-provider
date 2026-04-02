"""Scene for displaying stored exchange rates in Telegram bot UI."""

from typing import Any, ClassVar, cast

from aiogram.fsm.scene import on
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from rates_provider.application.list_exchange_rates import (
    ListExchangeRatesResult,
    ListExchangeRatesUseCase,
)
from rates_provider.infrastructure.telegram_bot.callbacks.my_rates import (
    ListRatesActionCallback,
    RatePairCallback,
)
from users_service.domain.user import User as InternalUser

from ..base import BaseTelegramScene
from ..shared.formatting import format_rate_value_plain
from ..shared.state_keys import SOURCE_CURRENCY_KEY, TARGET_CURRENCY_KEY
from .add_rate import AddRateSourceScene
from .selected_rate import SelectedRateScene


def _build_list_rates_lines(
    result: ListExchangeRatesResult,
    text_lines: list[str],
    prompt_text: str,
) -> list[str]:
    """Build text lines for the list-rates scene."""
    no_rates = "Курсы пока не добавлены."
    body = prompt_text if result.exchange_rates else no_rates
    return [*text_lines, "", body]


def _build_pairs_keyboard_rows(
    result: ListExchangeRatesResult,
) -> list[list[InlineKeyboardButton]]:
    """Build one button per currency pair for list state."""
    rows: list[list[InlineKeyboardButton]] = []
    for item in result.exchange_rates:
        pair_label = (
            f"{item.source_currency} -> {item.target_currency} = "
            f"{format_rate_value_plain(item.rate_value)}"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=pair_label,
                    callback_data=RatePairCallback(
                        source_currency=item.source_currency,
                        target_currency=item.target_currency,
                    ).pack(),
                )
            ]
        )
    return rows


class ListRatesScene(BaseTelegramScene, state="rates_list"):
    """Scene that shows active latest exchange rates with actions per pair."""
    _TEXT_LINES: ClassVar[list[str]] = ["Курсы обмена"]
    _PROMPT_TEXT: ClassVar[str] = "Выбери валютную пару из списка ниже."
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(
            text="Добавить курс",
            callback_data=ListRatesActionCallback().pack(),
        )
    ]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup for the stored exchange-rate list."""
        list_exchange_rates_use_case = cast(
            ListExchangeRatesUseCase,
            kwargs["list_exchange_rates_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        result = await list_exchange_rates_use_case.execute(current_user.user_id.value)

        text_lines = _build_list_rates_lines(
            result,
            text_lines=list(self._TEXT_LINES),
            prompt_text=self._PROMPT_TEXT,
        )
        text = "\n".join(text_lines)

        rows = self._configured_rows() + _build_pairs_keyboard_rows(result)
        markup = await self._build_markup(rows)
        return text, markup

    @on.callback_query(ListRatesActionCallback.filter())
    async def on_add_rate_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Open add-rate flow from list screen and keep back navigation to menu."""
        await callback_query.answer()
        await self.wizard.goto(AddRateSourceScene)

    @on.callback_query(RatePairCallback.filter())
    async def on_pair_click(
        self,
        callback_query: CallbackQuery,
        callback_data: RatePairCallback,
    ) -> None:
        """Open selected-rate scene after choosing pair from list buttons."""
        await callback_query.answer()
        await self.wizard.update_data(
            {
                SOURCE_CURRENCY_KEY: callback_data.source_currency,
                TARGET_CURRENCY_KEY: callback_data.target_currency,
            }
        )
        await self.wizard.goto(SelectedRateScene)

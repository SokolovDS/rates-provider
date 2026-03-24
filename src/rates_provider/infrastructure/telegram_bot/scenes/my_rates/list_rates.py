"""Scene for displaying stored exchange rates in Telegram bot UI."""

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from rates_provider.application.list_exchange_rates import (
    ListExchangeRatesResult,
    ListExchangeRatesUseCase,
)
from users_service.domain.user import User as InternalUser

from ..base import BaseTelegramScene
from ..shared.formatting import format_rate_value_plain
from ..shared.state_keys import (
    SELECTED_RATE_SOURCE_CURRENCY_KEY,
    SELECTED_RATE_TARGET_CURRENCY_KEY,
)
from .add_rate import AddRateSourceScene
from .selected_rate import SelectedRateScene

ADD_RATE_CALLBACK_DATA = "list_add_rate"
PAIR_CALLBACK_PREFIX = "rate_pair"


def _build_pair_callback_data(prefix: str, source_currency: str, target_currency: str) -> str:
    """Build callback payload for list item action scoped by currency pair."""
    return f"{prefix}:{source_currency}:{target_currency}"


def _parse_pair_callback_data(callback_data: str, prefix: str) -> tuple[str, str] | None:
    """Parse callback payload into source and target currencies."""
    expected_prefix = f"{prefix}:"
    if not callback_data.startswith(expected_prefix):
        return None

    payload = callback_data[len(expected_prefix):]
    parts = payload.split(":")
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def _build_list_rates_lines(result: ListExchangeRatesResult) -> list[str]:
    """Build user-facing text lines for pair list state."""
    if not result.exchange_rates:
        return ["Курсы обмена", "", "Курсы пока не добавлены."]

    return ["Курсы обмена", "", "Выбери валютную пару из списка ниже."]


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
                    callback_data=_build_pair_callback_data(
                        PAIR_CALLBACK_PREFIX,
                        item.source_currency,
                        item.target_currency,
                    ),
                )
            ]
        )
    return rows


class ListRatesScene(BaseTelegramScene, state="rates_list"):
    """Scene that shows active latest exchange rates with actions per pair."""

    async def _list_payload(
        self,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup for the stored exchange-rate list."""
        result = await list_exchange_rates_use_case.execute(current_user.user_id.value)
        text = "\n".join(_build_list_rates_lines(result))
        return text, await self._build_reply_markup(result)

    async def _build_reply_markup(
        self,
        result: ListExchangeRatesResult,
    ) -> InlineKeyboardMarkup | None:
        """Build markup with one button per active currency pair."""
        rows: list[list[InlineKeyboardButton]] = [
            [
                InlineKeyboardButton(
                    text="Добавить курс",
                    callback_data=ADD_RATE_CALLBACK_DATA,
                )
            ]
        ]
        rows.extend(_build_pairs_keyboard_rows(result))

        if await self._has_previous_scene():
            rows.append(
                [
                    InlineKeyboardButton(
                        text=self._BACK_BUTTON_TEXT,
                        callback_data=self._BACK_CALLBACK_DATA,
                    )
                ]
            )

        if not rows:
            return None
        return InlineKeyboardMarkup(inline_keyboard=rows)

    @on.callback_query(F.data == ADD_RATE_CALLBACK_DATA)
    async def on_add_rate_click(self, callback_query: CallbackQuery) -> None:
        """Open add-rate flow from list screen and keep back navigation to menu."""
        await callback_query.answer()
        await self.wizard.goto(AddRateSourceScene)

    @on.message.enter()
    async def on_enter_from_message(
        self,
        message: Message,
        list_exchange_rates_use_case: ListExchangeRatesUseCase,
        current_user: InternalUser,
    ) -> None:
        """Render list message when entered from a message event."""
        text, reply_markup = await self._list_payload(
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
        """Edit existing UI shell when list scene is opened from callback."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._list_payload(
            list_exchange_rates_use_case,
            current_user,
        )
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query(F.data.startswith(f"{PAIR_CALLBACK_PREFIX}:"))
    async def on_pair_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Open selected-rate scene after choosing pair from list buttons."""
        await callback_query.answer()
        callback_data = callback_query.data
        if not isinstance(callback_data, str):
            return

        parsed_pair = _parse_pair_callback_data(
            callback_data, PAIR_CALLBACK_PREFIX)
        if parsed_pair is None:
            return

        source_currency, target_currency = parsed_pair
        await self.wizard.update_data(
            {
                SELECTED_RATE_SOURCE_CURRENCY_KEY: source_currency,
                SELECTED_RATE_TARGET_CURRENCY_KEY: target_currency,
            }
        )
        await self.wizard.goto(SelectedRateScene)

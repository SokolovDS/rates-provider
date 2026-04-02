"""Rates submenu scene for Telegram bot UI."""

from typing import ClassVar

from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton

from ..callbacks.navigation import (
    RatesMenuCalculateReceivedCallback,
    RatesMenuCalculateRequiredCallback,
    RatesMenuFindPathsCallback,
    RatesMenuListCallback,
)
from .base import BaseTelegramScene
from .exchange_paths import (
    ExchangePathSourceScene,
    ReceivedAmountSourceScene,
    RequiredAmountSourceScene,
)
from .my_rates.list_rates import ListRatesScene


class RatesMenuScene(BaseTelegramScene, state="rates_menu"):
    """Scene that renders rates-related actions."""

    _TEXT_LINES: ClassVar[list[str]] = ["Курсы: выбери действие."]
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(
            text="Мои курсы", callback_data=RatesMenuListCallback().pack()),
        InlineKeyboardButton(
            text="Найти выгодный маршрут обмена",
            callback_data=RatesMenuFindPathsCallback().pack(),
        ),
        InlineKeyboardButton(
            text="Сколько получу за сумму",
            callback_data=RatesMenuCalculateReceivedCallback().pack(),
        ),
        InlineKeyboardButton(
            text="Сколько нужно для суммы",
            callback_data=RatesMenuCalculateRequiredCallback().pack(),
        ),
    ]

    @on.callback_query(RatesMenuListCallback.filter())
    async def on_list_rates_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Transition from rates submenu to stored-rates list scene."""
        await callback_query.answer()
        await self.wizard.goto(ListRatesScene)

    @on.callback_query(RatesMenuFindPathsCallback.filter())
    async def on_find_paths_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Transition from rates submenu to exchange-path source step."""
        await callback_query.answer()
        await self.wizard.goto(ExchangePathSourceScene)

    @on.callback_query(RatesMenuCalculateReceivedCallback.filter())
    async def on_calculate_received_amount_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Transition to flow that calculates target amount for source sum."""
        await callback_query.answer()
        await self.wizard.goto(ReceivedAmountSourceScene)

    @on.callback_query(RatesMenuCalculateRequiredCallback.filter())
    async def on_calculate_required_amount_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Transition to flow that calculates required source sum."""
        await callback_query.answer()
        await self.wizard.goto(RequiredAmountSourceScene)

"""Rates submenu scene for Telegram bot UI."""

from typing import ClassVar

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton

from .add_rate import AddRateSourceScene
from .base import BaseTelegramScene
from .exchange_paths import (
    ExchangePathSourceScene,
    ReceivedAmountSourceScene,
    RequiredAmountSourceScene,
)
from .list_rates import ListRatesScene


class RatesMenuScene(BaseTelegramScene, state="rates_menu"):
    """Scene that renders rates-related actions."""

    _TEXT_LINES: ClassVar[list[str]] = ["Курсы: выбери действие."]
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(text="Добавить курс", callback_data="add_rate"),
        InlineKeyboardButton(text="Показать все курсы",
                             callback_data="list_rates"),
        InlineKeyboardButton(
            text="Найти выгодный маршрут обмена",
            callback_data="find_paths",
        ),
        InlineKeyboardButton(
            text="Сколько получу за сумму",
            callback_data="calculate_received_amount",
        ),
        InlineKeyboardButton(
            text="Сколько нужно для суммы",
            callback_data="calculate_required_amount",
        ),
    ]

    @on.callback_query(F.data == "add_rate")
    async def on_add_rate_click(self, callback_query: CallbackQuery) -> None:
        """Transition from rates submenu to first add-rate step."""
        await callback_query.answer()
        await self.wizard.goto(AddRateSourceScene)

    @on.callback_query(F.data == "list_rates")
    async def on_list_rates_click(self, callback_query: CallbackQuery) -> None:
        """Transition from rates submenu to stored-rates list scene."""
        await callback_query.answer()
        await self.wizard.goto(ListRatesScene)

    @on.callback_query(F.data == "find_paths")
    async def on_find_paths_click(self, callback_query: CallbackQuery) -> None:
        """Transition from rates submenu to exchange-path source step."""
        await callback_query.answer()
        await self.wizard.goto(ExchangePathSourceScene)

    @on.callback_query(F.data == "calculate_received_amount")
    async def on_calculate_received_amount_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Transition to flow that calculates target amount for source sum."""
        await callback_query.answer()
        await self.wizard.goto(ReceivedAmountSourceScene)

    @on.callback_query(F.data == "calculate_required_amount")
    async def on_calculate_required_amount_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Transition to flow that calculates required source sum."""
        await callback_query.answer()
        await self.wizard.goto(RequiredAmountSourceScene)

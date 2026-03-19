"""Rates submenu scene for Telegram bot UI."""

from typing import ClassVar

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from .add_rate import AddRateSourceScene
from .base import BaseTelegramScene
from .list_rates import ListRatesScene


class RatesMenuScene(BaseTelegramScene, state="rates_menu"):
    """Scene that renders rates-related actions."""

    _TEXT_LINES: ClassVar[list[str]] = ["Курсы: выбери действие."]
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(text="Добавить курс", callback_data="add_rate"),
        InlineKeyboardButton(text="Показать все курсы",
                             callback_data="list_rates"),
    ]

    @on.message.enter()
    async def on_enter(self, message: Message) -> None:
        """Send submenu message when entered from a command/message."""
        text, reply_markup = await self._payload()
        await message.answer(text, reply_markup=reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(self, callback_query: CallbackQuery) -> None:
        """Edit existing UI shell when submenu is opened from callback."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._payload()
        await message.edit_text(text, reply_markup=reply_markup)

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

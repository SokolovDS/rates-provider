"""Main menu scene for Telegram bot UI."""

from typing import ClassVar

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
)

from .base import BaseTelegramScene
from .rates_menu import RatesMenuScene


class MainMenuScene(BaseTelegramScene, state="main_menu"):
    """Scene that renders the root action menu."""

    _TEXT_LINES: ClassVar[list[str]] = ["Это главное меню, выбери действие:"]
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(text="Курсы", callback_data="rates_menu")
    ]

    @on.callback_query(F.data == "rates_menu")
    async def on_rates_menu_click(self, callback_query: CallbackQuery) -> None:
        """Transition from main menu to rates submenu scene."""
        await callback_query.answer()
        await self.wizard.goto(RatesMenuScene)

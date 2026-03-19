"""Main menu scene for Telegram bot UI."""

from typing import ClassVar

from aiogram import F
from aiogram.fsm.scene import on
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .base import BaseTelegramScene
from .rates_menu import RatesMenuScene


class MainMenuScene(BaseTelegramScene, state="main_menu"):
    """Scene that renders the root action menu."""

    _MENU_TEXT: str = "Это главное меню, выбери действие:"
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(text="Курсы", callback_data="rates_menu")
    ]

    async def _menu_payload(self) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup used to render the main menu message."""
        return self._MENU_TEXT, await self.reply_markup()

    @on.message.enter()
    async def on_enter(self, message: Message) -> None:
        """Send a fresh menu message when entered from a command."""
        text, reply_markup = await self._menu_payload()
        await message.answer(text, reply_markup=reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(self, callback_query: CallbackQuery) -> None:
        """Edit existing UI shell when menu is opened from another scene."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._menu_payload()
        await message.edit_text(text, reply_markup=reply_markup)

    @on.callback_query(F.data == "rates_menu")
    async def on_rates_menu_click(self, callback_query: CallbackQuery) -> None:
        """Transition from main menu to rates submenu scene."""
        await callback_query.answer()
        await self.wizard.goto(RatesMenuScene)

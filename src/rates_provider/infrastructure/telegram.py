"""Telegram delivery mechanism implementation."""

from aiogram import Bot, Dispatcher
from aiogram.types import Message


async def echo_message(message: Message) -> None:
    """Copy any incoming message back to the same chat, preserving its content type."""
    await message.copy_to(message.chat.id)


def build_dispatcher() -> Dispatcher:
    """Build dispatcher with all message handlers registered."""
    dispatcher = Dispatcher()
    dispatcher.message()(echo_message)
    return dispatcher


async def run_echo_bot(token: str) -> None:
    """Start Telegram long polling for the echo bot."""
    bot = Bot(token=token)
    dispatcher = build_dispatcher()
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()

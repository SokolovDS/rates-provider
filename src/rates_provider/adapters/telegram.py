"""Telegram adapter implementation."""

from aiogram import Bot, Dispatcher
from aiogram.types import Message


def build_dispatcher() -> Dispatcher:
    """Build dispatcher with all message handlers registered."""
    dispatcher = Dispatcher()

    @dispatcher.message()
    async def echo_message(message: Message) -> None:
        """Reply with the exact same text for text messages."""
        if message.text is None:
            return
        await message.answer(message.text)

    return dispatcher


async def run_echo_bot(token: str) -> None:
    """Start Telegram long polling for the echo bot."""
    bot = Bot(token=token)
    dispatcher = build_dispatcher()
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()

"""Tests for the Telegram adapter echo handler."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from rates_provider.infrastructure.telegram import echo_message


def _make_message(**kwargs: Any) -> MagicMock:
    """Build a fake aiogram Message with copy_to mocked."""
    msg = MagicMock()
    msg.chat.id = 123
    msg.copy_to = AsyncMock()
    for key, value in kwargs.items():
        setattr(msg, key, value)
    return msg


def test_echo_copies_text_message() -> None:
    """Echo handler should copy a text message back to the same chat."""
    message = _make_message(text="hello")
    asyncio.run(echo_message(message))
    message.copy_to.assert_awaited_once_with(message.chat.id)


def test_echo_copies_sticker_message() -> None:
    """Echo handler should copy a sticker message back to the same chat."""
    message = _make_message(text=None, sticker=MagicMock())
    asyncio.run(echo_message(message))
    message.copy_to.assert_awaited_once_with(message.chat.id)


def test_echo_copies_photo_message() -> None:
    """Echo handler should copy a photo message back to the same chat."""
    message = _make_message(text=None, photo=[MagicMock()])
    asyncio.run(echo_message(message))
    message.copy_to.assert_awaited_once_with(message.chat.id)


def test_echo_copies_animation_message() -> None:
    """Echo handler should copy an animation (GIF) message back to the same chat."""
    message = _make_message(text=None, animation=MagicMock())
    asyncio.run(echo_message(message))
    message.copy_to.assert_awaited_once_with(message.chat.id)

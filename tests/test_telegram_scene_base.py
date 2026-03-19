"""Tests for shared base scene text rendering behavior."""

import asyncio
from typing import Any, cast

from rates_provider.infrastructure.telegram_bot.scenes.base import BaseTelegramScene


class _DummyTextBuilder:
    """Lightweight async text provider for base helper tests."""

    async def _create_base_lines(self) -> list[str]:
        """Provide deterministic base lines for tests."""
        return ["База"]


def test_get_text_appends_user_input_for_error() -> None:
    """Base _get_text should append formatted user input on error."""
    dummy = _DummyTextBuilder()

    result = asyncio.run(
        BaseTelegramScene._get_text(
            cast(Any, dummy),
            error_text="Ошибка",
            user_input=" usd ",
        )
    )

    assert result == "База\n\nОшибка\nВы ввели: usd"


def test_get_text_uses_empty_placeholder_for_blank_input() -> None:
    """Base _get_text should render placeholder for blank user input."""
    dummy = _DummyTextBuilder()

    result = asyncio.run(
        BaseTelegramScene._get_text(
            cast(Any, dummy),
            error_text="Ошибка",
            user_input="   ",
        )
    )

    assert result == "База\n\nОшибка\nВы ввели: <пусто>"

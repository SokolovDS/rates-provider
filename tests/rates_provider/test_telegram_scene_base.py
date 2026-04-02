"""Tests for shared base scene text rendering behavior."""

import asyncio
from typing import Any, cast

from rates_provider.infrastructure.telegram_bot.callbacks.navigation import (
    BackNavigationCallback,
)
from rates_provider.infrastructure.telegram_bot.scenes.base import (
    BaseTelegramScene,
    _prepare_scene_data_for_enter,
)


class _DummyTextBuilder:
    """Lightweight async text provider for base helper tests."""

    async def _create_base_lines(self) -> list[str]:
        """Provide deterministic base lines for tests."""
        return ["База"]


class _DummyDeclarativeScene:
    """Minimal scene-like object for declarative base line tests."""

    _TEXT_LINES = ["Заголовок"]
    _PROMPT_TEXT = "Подсказка"


async def _hook_with_named_kwargs(*, first: int) -> int:
    """Return a named kwarg to verify extra kwargs are filtered out."""
    return first


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


def test_create_base_lines_joins_title_and_prompt_text() -> None:
    """Base scene should build declarative text from title and prompt fields."""
    result = asyncio.run(BaseTelegramScene._create_base_lines(
        cast(Any, _DummyDeclarativeScene())))

    assert result == ["Заголовок", "", "Подсказка"]


def test_call_hook_filters_unsupported_kwargs() -> None:
    """Base line builder should ignore unsupported kwargs when calling hooks."""
    supported_kwargs = {"first": 1}
    unsupported_kwargs = {"second": 2}
    all_kwargs: dict[str, int] = {**supported_kwargs, **unsupported_kwargs}

    filtered_kwargs = {key: value for key, value in all_kwargs.items() if key in {"first"}}

    assert "second" not in filtered_kwargs
    assert asyncio.run(_hook_with_named_kwargs(**filtered_kwargs)) == 1
def test_prepare_scene_data_for_enter_keeps_ui_message_id_by_default() -> None:
    """Scene enter data should keep current UI shell unless explicitly reset."""
    original_data = {"ui_message_id": 123, "source_currency": "USD"}

    prepared_data = _prepare_scene_data_for_enter(
        original_data,
        ui_message_id_key="ui_message_id",
        fresh_ui_message=False,
    )

    assert prepared_data == original_data
    assert prepared_data is not original_data


def test_prepare_scene_data_for_enter_drops_ui_message_id_for_fresh_ui() -> None:
    """Scene enter data should drop UI shell id when a new message is required."""
    prepared_data = _prepare_scene_data_for_enter(
        {"ui_message_id": 123, "source_currency": "USD"},
        ui_message_id_key="ui_message_id",
        fresh_ui_message=True,
    )

    assert prepared_data == {"source_currency": "USD"}


def test_base_scene_exposes_back_callback_contract() -> None:
    """Base scene should use centralized callback payload for back action."""
    assert BaseTelegramScene._BACK_CALLBACK_DATA == BackNavigationCallback().pack()

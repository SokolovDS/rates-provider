"""Tests for delete-rate confirmation scene configuration."""

from interfaces.telegram_bot.callbacks.my_rates import (
    DeleteRateConfirmCallback,
)
from interfaces.telegram_bot.scenes.my_rates.delete_rate_confirm import (
    DeleteRateConfirmScene,
    _build_delete_success_text,
)


def test_delete_rate_confirm_scene_has_single_confirm_button() -> None:
    """Delete scene should expose one explicit confirmation action."""
    assert len(DeleteRateConfirmScene._BUTTONS) == 1
    assert DeleteRateConfirmScene._BUTTONS[0].text == "Удалить"
    assert DeleteRateConfirmScene._BUTTONS[0].callback_data == DeleteRateConfirmCallback(
    ).pack()


def test_build_delete_success_text_contains_selected_pair() -> None:
    """Delete scene should show removed pair in success confirmation text."""
    assert _build_delete_success_text(
        "USD", "EUR") == "Курс удален:\nUSD -> EUR"

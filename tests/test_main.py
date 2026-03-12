"""Tests for the application entrypoint and configuration."""

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest
from pytest import MonkeyPatch

import rates_provider.main as main_module
from rates_provider.config import load_bot_token


def test_load_bot_token_returns_env_value(monkeypatch: MonkeyPatch) -> None:
    """load_bot_token should return a non-empty configured token."""
    monkeypatch.setenv("TEST_TELEGRAM_BOT_TOKEN", "token-value")
    assert load_bot_token("TEST_TELEGRAM_BOT_TOKEN") == "token-value"


def test_load_bot_token_raises_for_missing_value(monkeypatch: MonkeyPatch) -> None:
    """load_bot_token should fail fast when token is not configured."""
    monkeypatch.delenv("TEST_TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="TEST_TELEGRAM_BOT_TOKEN"):
        load_bot_token("TEST_TELEGRAM_BOT_TOKEN")


def test_main_runs_echo_bot_with_loaded_token(monkeypatch: MonkeyPatch) -> None:
    """main should orchestrate token loading and coroutine execution."""
    captured_coroutine: Coroutine[Any, Any, None] | None = None

    monkeypatch.setattr(main_module, "load_bot_token",
                        lambda: "token-from-config")

    async def fake_run_echo_bot(token: str) -> None:
        """Fake coroutine for main orchestration test."""
        assert token == "token-from-config"

    def fake_asyncio_run(coroutine: Coroutine[Any, Any, None]) -> None:
        """Capture coroutine without running an event loop in test."""
        nonlocal captured_coroutine
        captured_coroutine = coroutine
        coroutine.close()

    monkeypatch.setattr(main_module, "run_echo_bot", fake_run_echo_bot)
    monkeypatch.setattr(asyncio, "run", fake_asyncio_run)

    main_module.main()

    assert captured_coroutine is not None

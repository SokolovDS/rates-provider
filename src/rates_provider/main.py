"""Application entrypoint implementation."""

import asyncio

from rates_provider.config import load_bot_token
from rates_provider.infrastructure.telegram_bot import run_bot


def main() -> None:
    """Run Telegram bot with configured application services."""
    token = load_bot_token()
    asyncio.run(run_bot(token))

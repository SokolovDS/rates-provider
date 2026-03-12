"""Application entrypoint implementation."""

import asyncio

from .adapters.telegram import run_echo_bot
from .config import load_bot_token


def main() -> None:
    """Run the Telegram echo bot."""
    token = load_bot_token()
    asyncio.run(run_echo_bot(token))

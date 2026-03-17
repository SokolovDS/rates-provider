"""Application entrypoint implementation."""

import asyncio

from .config import load_bot_token
from .infrastructure.telegram import run_echo_bot


def main() -> None:
    """Run the Telegram echo bot."""
    token = load_bot_token()
    asyncio.run(run_echo_bot(token))

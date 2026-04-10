"""Application entrypoint implementation."""

import asyncio

from app.bootstrap.config import load_bot_token
from interfaces.telegram_bot import run_bot


def main() -> None:
    """Run Telegram bot with configured application services."""
    token = load_bot_token()
    asyncio.run(run_bot(token))


if __name__ == "__main__":
    main()

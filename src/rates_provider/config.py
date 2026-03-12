"""Configuration loading for application runtime."""

import os

from dotenv import load_dotenv


def load_bot_token(env_var_name: str = "TELEGRAM_BOT_TOKEN") -> str:
    """Load the Telegram bot token from environment variables."""
    load_dotenv()
    token = os.getenv(env_var_name)
    if token is None or token.strip() == "":
        error_message = f"Environment variable {env_var_name} is required"
        raise RuntimeError(error_message)
    return token

# rates-provider

Python project with source code in `src/` and tests in `tests/`.

## Telegram Echo Bot

This project includes an asynchronous Telegram echo bot implementation.
The bot replies with exactly the same text it receives.

Set your bot token in `.env`:

```bash
cp .env.example .env
# then edit .env
# TELEGRAM_BOT_TOKEN=your_token_here
```

## Run

```bash
pip install -e .
python3 -m rates_provider
# or via console script:
rates-provider
```

## Checks

```bash
python3 -m pytest tests/ -v
ruff check .
mypy .
```
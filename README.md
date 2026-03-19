# rates-provider

Python project with source code in `src/` and tests in `tests/`.

## Telegram Bot UX

The bot provides a single-message UI shell with declarative callback actions.

Current Telegram behavior:

- `/start` always resets state and sends a new main menu message;
- main menu contains action `Курсы`;
- rates submenu contains actions: `Добавить курс` and `Показать все курсы`;
- add-rate flow is implemented via aiogram Scene Wizard API;
- after menu entry, the bot edits one UI message for further screens;
- non-menu screens include `Назад` button;
- user text messages are deleted on best effort after processing;
- add-rate flow is step-by-step: source currency -> target currency -> rate;
- `Назад` in add-rate flow uses scene wizard navigation (`wizard.back`);
- each next step re-shows already collected context lines;
- list screen shows all rates as `USD -> EUR = 90.50 (2026.03.19 11:00:00 UTC)`, newest first;
- storage remains in-memory, so records are lost after restart.

## Exchange Rate Use Cases

The project includes two application use cases:

- `AddExchangeRateUseCase` for adding a validated rate record;
- `ListExchangeRatesUseCase` for retrieving all records.

Current behavior:

- exchange rates are validated in the domain layer;
- currency codes are normalized to uppercase;
- repeated additions for the same pair are stored as history;
- all stored records can be retrieved via a dedicated list use case;
- storage is in-memory only, so records are lost on process restart.

Example usage from Python:

```python
import asyncio
from decimal import Decimal

from rates_provider.application.add_exchange_rate import (
	AddExchangeRateCommand,
	AddExchangeRateUseCase,
)
from rates_provider.application.list_exchange_rates import ListExchangeRatesUseCase
from rates_provider.infrastructure.memory_exchange_rate_repository import (
	InMemoryExchangeRateRepository,
)

repository = InMemoryExchangeRateRepository()
use_case = AddExchangeRateUseCase(repository)

result = asyncio.run(
	use_case.execute(
		AddExchangeRateCommand(
			source_currency="USD",
			target_currency="EUR",
			rate_value=Decimal("90.50"),
		)
	)
)

print(result)

list_use_case = ListExchangeRatesUseCase(repository)
all_rates = asyncio.run(list_use_case.execute())

print(all_rates.exchange_rates)
```

`ListExchangeRatesUseCase` returns records in insertion order.
If the repository is empty, it returns an empty tuple.

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
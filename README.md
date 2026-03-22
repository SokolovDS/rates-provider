# rates-provider

Python project with source code in `src/` and tests in `tests/`.

## Package Layout

- `src/rates_provider/` contains exchange-rate domain and Telegram bot flow.
- `src/users_service/` contains user lifecycle and external identity mapping.
- `tests/rates_provider/` contains rates-provider behavior tests.
- `tests/users_service/` contains users-service behavior tests.

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
- list screen shows only current user's rates as `USD -> EUR = 90.50 (2026.03.19 11:00:00 UTC)`, newest first;
- Telegram screens with route calculations show calculated rates and deviation percents rounded to 2 decimal places;
- rates are stored in SQLite, so records survive restarts.
- on any handled Telegram interaction (message or callback), user account is
	resolved-or-created in the internal User Service.

## Exchange Rate Use Cases

The project includes two application use cases:

- `AddExchangeRateUseCase` for adding a validated rate record;
- `ListExchangeRatesUseCase` for retrieving all records.
- `ComputeExchangePathsUseCase` for computing ranked exchange routes between two currencies.
- `ComputeReceivedAmountUseCase` for calculating how much target currency you get for a source amount.
- `ComputeRequiredSourceAmountUseCase` for calculating how much source currency is needed for a target amount.

Current behavior:

- exchange rates are validated in the domain layer;
- currency codes are normalized to uppercase;
- repeated additions for the same pair are stored as history;
- rates are isolated by internal user id;
- user-specific records can be retrieved via a dedicated list use case;
- profitable exchange routes can be built across intermediate currencies;
- routes are sorted from the best effective rate to the worst;
- each route includes signed deviation percent from the best route;
- you can calculate target amount received for a given source amount across all valid routes;
- you can calculate source amount required for a given target amount across all valid routes;
- storage uses SQLite file persistence.

Example usage from Python:

```python
import asyncio
from decimal import Decimal

from rates_provider.application.add_exchange_rate import (
	AddExchangeRateCommand,
	AddExchangeRateUseCase,
)
from rates_provider.application.list_exchange_rates import ListExchangeRatesUseCase
from rates_provider.application.compute_exchange_paths import (
	ComputeExchangePathsCommand,
	ComputeExchangePathsUseCase,
	ComputeReceivedAmountCommand,
	ComputeReceivedAmountUseCase,
	ComputeRequiredSourceAmountCommand,
	ComputeRequiredSourceAmountUseCase,
)
from rates_provider.infrastructure.sqlite_exchange_rate_repository import (
	SQLiteExchangeRateRepository,
)

repository = SQLiteExchangeRateRepository("data/exchange_rates.sqlite3")
use_case = AddExchangeRateUseCase(repository)

result = asyncio.run(
	use_case.execute(
		AddExchangeRateCommand(
			user_id="user-1",
			source_currency="USD",
			target_currency="EUR",
			rate_value=Decimal("90.50"),
		)
	)
)

print(result)

list_use_case = ListExchangeRatesUseCase(repository)
all_rates = asyncio.run(list_use_case.execute("user-1"))

print(all_rates.exchange_rates)

paths_use_case = ComputeExchangePathsUseCase(repository)
paths_result = asyncio.run(
	paths_use_case.execute(
		ComputeExchangePathsCommand(
			user_id="user-1",
			source_currency="RUB",
			target_currency="THB",
		)
	)
)

for path in paths_result.paths:
	print(path.currencies, path.effective_rate, path.deviation_percent)

received_amount_use_case = ComputeReceivedAmountUseCase(repository)
received_amount_result = asyncio.run(
	received_amount_use_case.execute(
		ComputeReceivedAmountCommand(
			user_id="user-1",
			source_currency="RUB",
			target_currency="THB",
			source_amount=Decimal("1000"),
		)
	)
)

required_source_use_case = ComputeRequiredSourceAmountUseCase(repository)
required_source_result = asyncio.run(
	required_source_use_case.execute(
		ComputeRequiredSourceAmountCommand(
			user_id="user-1",
			source_currency="RUB",
			target_currency="THB",
			target_amount=Decimal("5000"),
		)
	)
)
```

`ListExchangeRatesUseCase` returns records in insertion order.
If the repository is empty, it returns an empty tuple.

`ComputeExchangePathsUseCase` rules:

- only user-specific rates are considered;
- routes are directed and use simple paths (no repeated currencies);
- maximum route length is 4 exchanges;
- `source == target` is rejected as validation error.

`ComputeReceivedAmountUseCase` and `ComputeRequiredSourceAmountUseCase` reuse the same route rules and additionally:

- requested amount must be positive;
- results are sorted from the most profitable route to the least profitable one;
- deviation percent stays signed relative to the best result.

Set your bot token in `.env`:

```bash
cp .env.example .env
# then edit .env
# TELEGRAM_BOT_TOKEN=your_token_here
# STORAGE_BACKEND=sqlite
# SQLITE_RATES_DB_PATH=data/exchange_rates.sqlite3
# SQLITE_USERS_DB_PATH=data/users_service.sqlite3
```

Storage backend options:

- `STORAGE_BACKEND=sqlite` (default) uses persistent SQLite file storage;
- `STORAGE_BACKEND=memory` uses volatile in-memory storage.

For sqlite backend, services use separate databases:

- Rates Provider DB: `SQLITE_RATES_DB_PATH`;
- Users Service DB: `SQLITE_USERS_DB_PATH`.

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
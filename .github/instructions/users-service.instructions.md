---
description: "Use when editing Users Service context in top-level users_service package."
applyTo: "src/users_service/**/*.py,tests/users_service/**/*.py"
---

# Users Service Context Rules

## Scope

- Keep all user lifecycle and identity mapping logic in `src/users_service/`.
- Do not place users service domain/application/infrastructure modules under `src/rates_provider/`.
- Keep users service provider-agnostic in domain/application (Telegram specifics allowed only in users_service infrastructure telegram adapters).

## Boundaries

- `users_service/domain` must not import any infrastructure module.
- `users_service/application` may depend on `users_service/domain` only.
- `users_service/infrastructure` may depend on users_service domain/application ports.
- Never import `rates_provider.infrastructure` from users_service code.
- `rates_provider` may consume users_service through composition points and application-level contracts.

## Testing

- Place users service tests under `tests/users_service/`.
- Keep tests typed and deterministic; prefer unit tests for domain and use cases.
- Keep SQLite repository tests isolated with temporary paths.

## Verification

- Run `pytest tests/users_service -v` for focused checks.
- Run full checks before finalizing: `pytest tests -v`, `ruff check .`, `mypy .`.

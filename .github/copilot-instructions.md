# Copilot Instructions

## Project Intent

- Treat this repository as a Python provider aggregator for exchange rates.
- Keep domain logic independent from external integrations and I/O concerns.

## Architecture Rules

- Organize the code by domain areas with clear boundaries between them.
- Keep application source code under the `src/` directory; avoid placing Python source modules at repository root.
- Keep bounded contexts explicit at top-level packages under `src/`:
- `rates_provider/` for exchange-rate bot and rates domain.
- `users_service/` for user lifecycle and identity mapping.
- Use a Clean Architecture + DDD package layout with explicit layers:
- `domain/` for entities, value objects, domain services, domain events, and repository interfaces.
- `application/` for use cases, application services, commands/queries, and DTOs.
- `infrastructure/` for framework-dependent and I/O code (Telegram delivery, provider HTTP clients, persistence, messaging).
- Do not mix domain logic with provider integrations, transport, storage, or messaging code.
- Keep cross-context dependency direction strict:
- `rates_provider` code must not import `users_service.infrastructure`.
- `users_service` code must not import `rates_provider.infrastructure`.
- Composition/wiring is allowed in infrastructure composition points only.
- Prefer event-driven coordination between application components when it reduces direct coupling.
- Keep domain events explicit and named in business terms, not infrastructure terms.
- Keep application orchestration separate from domain rules.

## Python Conventions

- Typing is mandatory everywhere in Python code.
- Prefer small functions, readable names, and straightforward control flow.
- Do not add dependencies unless they clearly simplify the design.
- Prefer enforceable lint and type-check rules over informal style-only guidance.

## Change Expectations

- Update nearby documentation when behavior or usage changes.
- Ensure Python changes pass configured checks: `ruff check .` and `mypy .`.
- If tests were not run, state that clearly in the final response.

## Testing Expectations

- Follow TDD when implementing behavior: write or update the failing test first, then implement the code to satisfy it.
- Follow the testing pyramid: prefer many fast unit tests, fewer integration tests, and only a small number of end-to-end tests.
- Keep unit tests focused on domain rules, normalization, and application behavior without real external calls.
- Use integration tests for boundaries between application and infrastructure, but keep provider and network dependencies mocked or isolated.
- Keep tests separated by bounded context:
- `tests/rates_provider/` for rates and Telegram rates flow behavior.
- `tests/users_service/` for users service behavior.

## Telegram UI Policy

- Treat Telegram UX behavior as an explicit contract, not an implementation detail.
- When editing Telegram infrastructure code, follow the scoped rules in `.github/instructions/telegram-ui.instructions.md`.
- If Telegram UX behavior changes, update both tests and README in the same change.
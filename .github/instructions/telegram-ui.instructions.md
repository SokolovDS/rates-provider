---
description: "Use when editing Telegram bot infrastructure UI flow. Declares required single-message UX behavior, callback menu behavior, and context-rich prompts."
applyTo: "src/rates_provider/infrastructure/**/*.py"
---

# Telegram UI Contract

## Core UX Rules

- Keep a single visible bot UI message per chat during the add-rate flow.
- Update UI by editing the existing bot message text and markup instead of sending new step messages.
- Use inline keyboards for step controls and main actions; do not use reply keyboards for step navigation.
- Start menu must be available via /start and provide an action button to launch add-rate flow.
- /start must send a new menu message and must not edit the previous UI shell.

## Step Context Rules

- Each next-step prompt must include already collected context above the prompt text.
- Before target currency prompt, show source currency.
- Before rate prompt, show source and target currencies.
- Validation errors must preserve and re-show available context for the same step.
- Each add-rate step must provide an inline `Назад` button.
- `Назад` from source step returns to menu.
- `Назад` from target step returns to source step.
- `Назад` from rate step returns to target step while preserving selected source currency.

## Message Lifecycle Rules

- Attempt to delete user input messages after processing.
- User message deletion failures must not break the flow.
- Keep technical UI identity key stable in FSM data (ui_message_id).
- Keep business keys stable in FSM data (source_currency, target_currency).

## Architecture Boundaries

- Keep Telegram handlers in infrastructure layer only.
- Do not move domain validation rules into Telegram handlers.
- Do not change application use-case contracts for UI-only tasks.
- Avoid reintroducing a generic echo path that conflicts with single-message UI flow.

## Testing Requirements

- Follow TDD: update failing tests first, then implement behavior.
- tests/test_add_rate_dialog.py must verify:
- Context lines appear in edited message text for each step.
- Callback and command entry paths both work.
- Existing UI message is edited when ui_message_id exists.
- User message deletion is attempted.
- Error paths preserve context and stay on the same step.

## Verification Checklist

- Run: pytest tests/test_add_rate_dialog.py -v
- Run: pytest tests -v
- Run: ruff check .
- Run: mypy .
- Manually verify /start, button click, contextual prompts, and single-message behavior.

## Documentation Sync

- If Telegram UI behavior changes, update README Telegram section in the same change.
- Keep instruction wording aligned with tested behavior.

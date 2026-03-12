---
description: "Use when editing Python source files or tests. Applies Python coding conventions, readability rules, type hints, and formatting expectations."
applyTo: "**/*.py"
---

# Python Coding Conventions

## Python Instructions

- Typing is mandatory everywhere: all functions, methods, variables, class attributes, and return values must be annotated.
- Prefer small functions and straightforward control flow; split complex logic into smaller units.
- Docstrings are mandatory for all modules, classes, and functions — public and private alike.
- Add comments only when they explain non-obvious intent, tradeoffs, or design decisions.
- Use the `typing` module and modern Python typing syntax to keep contracts explicit.
- Handle edge cases explicitly and raise clear exceptions when behavior cannot be expressed safely.

## General Instructions

- Prioritize readability, clarity, and maintainability over cleverness.
- Keep code idiomatic and consistent with established Python best practices.
- When implementing algorithms or normalization logic, make the approach easy to follow.
- Keep external library usage explicit and limited to places where it simplifies the design.
- Prefer enforceable checks in linters and type checkers over manual style-only guidance.
- Code must pass configured lint and type checks before considering the task done.

## Environment

- This project runs inside a devcontainer. Do not create or use a virtual environment (`venv`); the devcontainer provides the Python environment directly.
- Run checks and tests with the system `python3` / `pytest` available on `PATH`.

## Linting And Type Checking

- Follow project Ruff and MyPy configuration from `pyproject.toml`.
- Required checks: `ruff check .` and `mypy .`.
- Do not bypass rules unless the change explicitly updates linter configuration with a clear rationale.
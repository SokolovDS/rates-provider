"""Architecture tests for module boundary rules in the new package structure."""

from __future__ import annotations

import ast
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = WORKSPACE_ROOT / "src"

MODULES = [
    "identity",
    "market_rates",
    "user_rates",
    "quote_engine",
    "quote_history",
]


def _iter_python_files(root: Path) -> list[Path]:
    """Return all Python files under a directory excluding cache folders."""
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _extract_import_modules(file_path: Path) -> set[str]:
    """Extract absolute imported module names from Python source file AST."""
    tree = ast.parse(file_path.read_text(
        encoding="utf-8"), filename=str(file_path))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module is not None:
                imported_modules.add(node.module)

    return imported_modules


def _collect_forbidden_imports(
    source_root: Path,
    forbidden_prefix: str,
    *,
    allowlist: set[str] | None = None,
) -> list[str]:
    """Collect file-to-import matches that violate forbidden prefix rule."""
    violations: list[str] = []
    effective_allowlist = allowlist or set()

    for file_path in _iter_python_files(source_root):
        relative_path = file_path.relative_to(WORKSPACE_ROOT).as_posix()
        if relative_path in effective_allowlist:
            continue

        imported_modules = _extract_import_modules(file_path)
        forbidden_matches = sorted(
            module
            for module in imported_modules
            if module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        )
        for forbidden_module in forbidden_matches:
            violations.append(f"{relative_path} imports {forbidden_module}")

    return violations


def test_module_domain_does_not_import_other_module_internals() -> None:
    """Each module's domain layer must not import another module's domain,
    application, or infrastructure.
    """
    violations: list[str] = []
    for module in MODULES:
        domain_path = SRC_ROOT / "modules" / module / "domain"
        if not domain_path.exists():
            continue
        for other_module in MODULES:
            if other_module == module:
                continue
            for layer in ("domain", "application", "infrastructure"):
                prefix = f"modules.{other_module}.{layer}"
                violations.extend(
                    _collect_forbidden_imports(domain_path, prefix))
    assert violations == [], "\n".join(violations)


def test_module_application_does_not_import_other_module_non_contracts() -> None:
    """Each module's application layer may only import another module's contracts layer."""
    violations: list[str] = []
    for module in MODULES:
        app_path = SRC_ROOT / "modules" / module / "application"
        if not app_path.exists():
            continue
        for other_module in MODULES:
            if other_module == module:
                continue
            for layer in ("domain", "application", "infrastructure"):
                prefix = f"modules.{other_module}.{layer}"
                violations.extend(_collect_forbidden_imports(app_path, prefix))
    assert violations == [], "\n".join(violations)


def test_interfaces_telegram_bot_does_not_import_module_infrastructure() -> None:
    """Telegram interface must not directly import module infrastructure
    (except identity telegram middleware).
    """
    telegram_path = SRC_ROOT / "interfaces" / "telegram_bot"
    if not telegram_path.exists():
        return
    violations: list[str] = []
    allowlist = {
        # bootstrap __init__ is the sole wiring point
        "src/interfaces/telegram_bot/__init__.py",
    }
    for module in MODULES:
        prefix = f"modules.{module}.infrastructure"
        violations.extend(
            _collect_forbidden_imports(
                telegram_path, prefix, allowlist=allowlist)
        )
    assert violations == [], "\n".join(violations)


def test_app_bootstrap_is_sole_cross_module_composition_root() -> None:
    """Module internals must not import bootstrap wiring
    (composition only at interface/bootstrap level).
    """
    modules_path = SRC_ROOT / "modules"
    assert modules_path.exists(), (
        f"Expected modules directory to exist for architecture checks: {modules_path}"
    )
    violations = _collect_forbidden_imports(
        modules_path, "app.bootstrap.wiring")
    assert violations == [], "\n".join(violations)

"""Architecture tests for cross-context infrastructure import boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RATES_INFRA_PATH = WORKSPACE_ROOT / "src" / "rates_provider" / "infrastructure"
USERS_INFRA_PATH = WORKSPACE_ROOT / "src" / "users_service" / "infrastructure"

# Temporary composition-point exceptions while runtime wiring stays in
# rates_provider infrastructure. Any new exceptions should be treated as a regression.
RATES_TO_USERS_INFRA_ALLOWLIST = {
    "src/rates_provider/infrastructure/repository_factory.py",
    "src/rates_provider/infrastructure/telegram_bot/__init__.py",
}


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


def test_users_service_infrastructure_does_not_import_rates_provider_infrastructure() -> None:
    """Users service infrastructure should not depend on rates provider infrastructure."""
    violations = _collect_forbidden_imports(
        USERS_INFRA_PATH,
        "rates_provider.infrastructure",
    )
    assert violations == []


def test_rates_provider_infrastructure_does_not_import_users_service_infrastructure() -> None:
    """Rates provider infrastructure should avoid users service infrastructure imports."""
    violations = _collect_forbidden_imports(
        RATES_INFRA_PATH,
        "users_service.infrastructure",
        allowlist=RATES_TO_USERS_INFRA_ALLOWLIST,
    )
    assert violations == []

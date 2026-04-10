"""Tests for computing all exchange paths and ranking by effective rate."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from modules.quote_engine.application.compute_exchange_paths import (
    ComputeExchangePathsUseCase,
    ComputeReceivedAmountUseCase,
    ComputeRequiredSourceAmountUseCase,
)
from modules.quote_engine.application.dtos import (
    ComputeExchangePathsCommand,
    ComputeReceivedAmountCommand,
    ComputeRequiredSourceAmountCommand,
)
from modules.quote_engine.domain.exceptions import NoExchangePathError, NonPositiveAmountError
from modules.user_rates.contracts.dtos import RateEntry
from modules.user_rates.contracts.reader_port import UserRatesReaderPort
from modules.user_rates.domain.exceptions import IdenticalCurrencyPairError


class PreloadedUserRatesReader(UserRatesReaderPort):
    """Reader test double returning predefined user-scoped rate entries."""

    def __init__(self, rates_by_user: dict[str, Sequence[RateEntry]]) -> None:
        """Initialize reader state with user-scoped rate entries."""
        self._rates_by_user = {
            user_id: tuple(entries)
            for user_id, entries in rates_by_user.items()
        }

    async def list_rates(self, user_id: str) -> Sequence[RateEntry]:
        """Return all predefined rates for a specific user."""
        return self._rates_by_user.get(user_id, tuple())


def _rate_entry(source: str, target: str, value: str) -> RateEntry:
    """Build deterministic rate entry for test scenarios."""
    return RateEntry(
        source_currency=source,
        target_currency=target,
        rate_value=Decimal(value),
        created_at=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
    )


def test_compute_exchange_paths_returns_all_routes_sorted_best_to_worst() -> None:
    """Use case should return all simple paths sorted by effective rate desc."""
    reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "USD", "80"),
                _rate_entry("RUB", "CNY", "10"),
                _rate_entry("CNY", "THB", "30"),
                _rate_entry("USD", "THB", "20"),
                _rate_entry("USD", "CNY", "25"),
                _rate_entry("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeExchangePathsUseCase(reader)

    result = asyncio.run(
        use_case.execute(
            ComputeExchangePathsCommand(
                user_id="user-1",
                source_currency="RUB",
                target_currency="THB",
            )
        )
    )

    assert result.best_rate == Decimal("60000")
    assert [path.currencies for path in result.paths] == [
        ("RUB", "USD", "CNY", "THB"),
        ("RUB", "USD", "THB"),
        ("RUB", "CNY", "THB"),
        ("RUB", "THB"),
    ]
    assert [path.effective_rate for path in result.paths] == [
        Decimal("60000"),
        Decimal("1600"),
        Decimal("300"),
        Decimal("5"),
    ]
    assert result.paths[0].deviation_percent == Decimal("0")
    assert result.paths[1].deviation_percent < Decimal("0")


def test_compute_exchange_paths_rejects_identical_source_and_target() -> None:
    """Use case should reject path lookup when currencies are identical."""
    reader = PreloadedUserRatesReader({"user-1": []})
    use_case = ComputeExchangePathsUseCase(reader)

    with pytest.raises(IdenticalCurrencyPairError, match="must differ"):
        asyncio.run(
            use_case.execute(
                ComputeExchangePathsCommand(
                    user_id="user-1",
                    source_currency="RUB",
                    target_currency="RUB",
                )
            )
        )


def test_compute_exchange_paths_rejects_blank_user_id() -> None:
    """Use case should reject blank user identifiers."""
    reader = PreloadedUserRatesReader({"user-1": []})
    use_case = ComputeExchangePathsUseCase(reader)

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(
            use_case.execute(
                ComputeExchangePathsCommand(
                    user_id="   ",
                    source_currency="RUB",
                    target_currency="THB",
                )
            )
        )


def test_compute_exchange_paths_isolated_per_user_scope() -> None:
    """Use case should only use exchange rates belonging to requested user."""
    reader = PreloadedUserRatesReader(
        {
            "user-1": [_rate_entry("RUB", "USD", "80")],
            "user-2": [_rate_entry("USD", "THB", "20")],
        }
    )
    use_case = ComputeExchangePathsUseCase(reader)

    with pytest.raises(NoExchangePathError, match="No exchange path"):
        asyncio.run(
            use_case.execute(
                ComputeExchangePathsCommand(
                    user_id="user-1",
                    source_currency="RUB",
                    target_currency="THB",
                )
            )
        )


def test_compute_exchange_paths_limits_maximum_exchanges_to_four() -> None:
    """Use case should skip paths that require more than four exchanges."""
    reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "AAA", "2"),
                _rate_entry("AAA", "AAB", "2"),
                _rate_entry("AAB", "AAC", "2"),
                _rate_entry("AAC", "AAD", "2"),
                _rate_entry("AAD", "THB", "2"),
            ]
        }
    )
    use_case = ComputeExchangePathsUseCase(reader)

    with pytest.raises(NoExchangePathError, match="No exchange path"):
        asyncio.run(
            use_case.execute(
                ComputeExchangePathsCommand(
                    user_id="user-1",
                    source_currency="RUB",
                    target_currency="THB",
                )
            )
        )


def test_compute_exchange_paths_excludes_cyclic_routes() -> None:
    """Use case should only return simple paths without repeated currencies."""
    reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "USD", "2"),
                _rate_entry("USD", "RUB", "2"),
                _rate_entry("USD", "THB", "3"),
                _rate_entry("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeExchangePathsUseCase(reader)

    result = asyncio.run(
        use_case.execute(
            ComputeExchangePathsCommand(
                user_id="user-1",
                source_currency="RUB",
                target_currency="THB",
            )
        )
    )

    assert ("RUB", "USD", "RUB", "THB") not in [
        path.currencies for path in result.paths]


def test_compute_received_amount_returns_all_routes_sorted_best_to_worst() -> None:
    """Use case should compute received target amount for each valid route."""
    reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "USD", "80"),
                _rate_entry("RUB", "CNY", "10"),
                _rate_entry("CNY", "THB", "30"),
                _rate_entry("USD", "THB", "20"),
                _rate_entry("USD", "CNY", "25"),
                _rate_entry("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeReceivedAmountUseCase(reader)

    result = asyncio.run(
        use_case.execute(
            ComputeReceivedAmountCommand(
                user_id="user-1",
                source_currency="RUB",
                target_currency="THB",
                source_amount=Decimal("2"),
            )
        )
    )

    assert result.best_target_amount == Decimal("120000")
    assert [path.target_amount for path in result.paths] == [
        Decimal("120000"),
        Decimal("3200"),
        Decimal("600"),
        Decimal("10"),
    ]
    assert result.paths[0].deviation_percent == Decimal("0")
    assert result.paths[-1].deviation_percent < Decimal("0")


def test_compute_required_source_amount_returns_all_routes_sorted_best_to_worst() -> None:
    """Use case should compute required source amount for each valid route."""
    reader = PreloadedUserRatesReader(
        {
            "user-1": [
                _rate_entry("RUB", "USD", "80"),
                _rate_entry("RUB", "CNY", "10"),
                _rate_entry("CNY", "THB", "30"),
                _rate_entry("USD", "THB", "20"),
                _rate_entry("USD", "CNY", "25"),
                _rate_entry("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeRequiredSourceAmountUseCase(reader)

    result = asyncio.run(
        use_case.execute(
            ComputeRequiredSourceAmountCommand(
                user_id="user-1",
                source_currency="RUB",
                target_currency="THB",
                target_amount=Decimal("600"),
            )
        )
    )

    assert result.best_source_amount == Decimal("0.01")
    assert [path.source_amount for path in result.paths] == [
        Decimal("0.01"),
        Decimal("0.375"),
        Decimal("2"),
        Decimal("120"),
    ]
    assert result.paths[0].deviation_percent == Decimal("0")
    assert result.paths[-1].deviation_percent < Decimal("0")


def test_compute_received_amount_rejects_non_positive_amount() -> None:
    """Received-amount scenario should reject non-positive source amount."""
    reader = PreloadedUserRatesReader({"user-1": []})
    use_case = ComputeReceivedAmountUseCase(reader)

    with pytest.raises(NonPositiveAmountError, match="positive"):
        asyncio.run(
            use_case.execute(
                ComputeReceivedAmountCommand(
                    user_id="user-1",
                    source_currency="RUB",
                    target_currency="THB",
                    source_amount=Decimal("0"),
                )
            )
        )


def test_compute_required_source_amount_rejects_non_positive_amount() -> None:
    """Required-source scenario should reject non-positive target amount."""
    reader = PreloadedUserRatesReader({"user-1": []})
    use_case = ComputeRequiredSourceAmountUseCase(reader)

    with pytest.raises(NonPositiveAmountError, match="positive"):
        asyncio.run(
            use_case.execute(
                ComputeRequiredSourceAmountCommand(
                    user_id="user-1",
                    source_currency="RUB",
                    target_currency="THB",
                    target_amount=Decimal("0"),
                )
            )
        )

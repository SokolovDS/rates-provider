"""Tests for computing all exchange paths and ranking by effective rate."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from rates_provider.application.compute_exchange_paths import (
    ComputeExchangePathsCommand,
    ComputeExchangePathsUseCase,
    ComputeReceivedAmountCommand,
    ComputeReceivedAmountUseCase,
    ComputeRequiredSourceAmountCommand,
    ComputeRequiredSourceAmountUseCase,
)
from rates_provider.domain.exceptions import (
    IdenticalCurrencyPairError,
    NoExchangePathError,
    NonPositiveAmountError,
)
from rates_provider.domain.exchange_rate import CurrencyCode, ExchangeRate
from rates_provider.domain.repositories import ExchangeRateRepository


class PreloadedExchangeRateRepository(ExchangeRateRepository):
    """Repository test double returning predefined user-scoped rates."""

    def __init__(self, rates_by_user: dict[str, Sequence[ExchangeRate]]) -> None:
        """Initialize repository state with user-scoped exchange rates."""
        self._rates_by_user = {
            user_id: tuple(exchange_rates)
            for user_id, exchange_rates in rates_by_user.items()
        }

    async def add(self, user_id: str, exchange_rate: ExchangeRate) -> None:
        """Append operation is unsupported for this read-only test double."""
        raise NotImplementedError

    async def list_all(self, user_id: str) -> Sequence[ExchangeRate]:
        """Return all predefined rates for a specific user."""
        return self._rates_by_user.get(user_id, tuple())


def _exchange_rate(source: str, target: str, value: str) -> ExchangeRate:
    """Build deterministic exchange-rate entity for test scenarios."""
    return ExchangeRate(
        source_currency=CurrencyCode(source),
        target_currency=CurrencyCode(target),
        rate_value=Decimal(value),
        created_at=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
    )


def test_compute_exchange_paths_returns_all_routes_sorted_best_to_worst() -> None:
    """Use case should return all simple paths sorted by effective rate desc."""
    repository = PreloadedExchangeRateRepository(
        {
            "user-1": [
                _exchange_rate("RUB", "USD", "80"),
                _exchange_rate("RUB", "CNY", "10"),
                _exchange_rate("CNY", "THB", "30"),
                _exchange_rate("USD", "THB", "20"),
                _exchange_rate("USD", "CNY", "25"),
                _exchange_rate("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeExchangePathsUseCase(repository)

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
    repository = PreloadedExchangeRateRepository({"user-1": []})
    use_case = ComputeExchangePathsUseCase(repository)

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
    repository = PreloadedExchangeRateRepository({"user-1": []})
    use_case = ComputeExchangePathsUseCase(repository)

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
    repository = PreloadedExchangeRateRepository(
        {
            "user-1": [_exchange_rate("RUB", "USD", "80")],
            "user-2": [_exchange_rate("USD", "THB", "20")],
        }
    )
    use_case = ComputeExchangePathsUseCase(repository)

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
    repository = PreloadedExchangeRateRepository(
        {
            "user-1": [
                _exchange_rate("RUB", "AAA", "2"),
                _exchange_rate("AAA", "AAB", "2"),
                _exchange_rate("AAB", "AAC", "2"),
                _exchange_rate("AAC", "AAD", "2"),
                _exchange_rate("AAD", "THB", "2"),
            ]
        }
    )
    use_case = ComputeExchangePathsUseCase(repository)

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
    repository = PreloadedExchangeRateRepository(
        {
            "user-1": [
                _exchange_rate("RUB", "USD", "2"),
                _exchange_rate("USD", "RUB", "2"),
                _exchange_rate("USD", "THB", "3"),
                _exchange_rate("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeExchangePathsUseCase(repository)

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
    repository = PreloadedExchangeRateRepository(
        {
            "user-1": [
                _exchange_rate("RUB", "USD", "80"),
                _exchange_rate("RUB", "CNY", "10"),
                _exchange_rate("CNY", "THB", "30"),
                _exchange_rate("USD", "THB", "20"),
                _exchange_rate("USD", "CNY", "25"),
                _exchange_rate("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeReceivedAmountUseCase(repository)

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
    repository = PreloadedExchangeRateRepository(
        {
            "user-1": [
                _exchange_rate("RUB", "USD", "80"),
                _exchange_rate("RUB", "CNY", "10"),
                _exchange_rate("CNY", "THB", "30"),
                _exchange_rate("USD", "THB", "20"),
                _exchange_rate("USD", "CNY", "25"),
                _exchange_rate("RUB", "THB", "5"),
            ]
        }
    )
    use_case = ComputeRequiredSourceAmountUseCase(repository)

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
    repository = PreloadedExchangeRateRepository({"user-1": []})
    use_case = ComputeReceivedAmountUseCase(repository)

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
    repository = PreloadedExchangeRateRepository({"user-1": []})
    use_case = ComputeRequiredSourceAmountUseCase(repository)

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

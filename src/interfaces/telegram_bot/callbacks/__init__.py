"""Centralized callback payload contracts for Telegram bot scenes."""

from .exchange_paths import (
    ExchangePathsResultCallback,
)
from .my_rates import (
    DeleteRateConfirmCallback,
    ListRatesActionCallback,
    RatePairCallback,
    SelectedRateDeleteCallback,
    SelectedRateEditCallback,
)
from .navigation import (
    BackNavigationCallback,
    MainMenuCallback,
    RatesMenuCalculateReceivedCallback,
    RatesMenuCalculateRequiredCallback,
    RatesMenuFindPathsCallback,
    RatesMenuListCallback,
)

__all__ = [
    "BackNavigationCallback",
    "DeleteRateConfirmCallback",
    "ExchangePathsResultCallback",
    "ListRatesActionCallback",
    "MainMenuCallback",
    "RatePairCallback",
    "RatesMenuCalculateReceivedCallback",
    "RatesMenuCalculateRequiredCallback",
    "RatesMenuFindPathsCallback",
    "RatesMenuListCallback",
    "SelectedRateDeleteCallback",
    "SelectedRateEditCallback",
]

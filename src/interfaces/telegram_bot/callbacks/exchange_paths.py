"""CallbackData contracts for exchange-path scene actions."""

from aiogram.filters.callback_data import CallbackData


class ExchangePathSourceCurrencyCallback(CallbackData, prefix="paths_source"):
    """Payload contract for source-currency selection in exchange-path flows."""

    currency: str


class ExchangePathTargetCurrencyCallback(CallbackData, prefix="paths_target"):
    """Payload contract for target-currency selection in exchange-path flows."""

    currency: str


class ExchangePathsResultCallback(CallbackData, prefix="paths_result"):
    """Payload contract for exchange-path result scene actions."""

    pass

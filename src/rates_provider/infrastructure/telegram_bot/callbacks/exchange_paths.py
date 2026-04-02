"""CallbackData contracts for exchange-paths result actions."""

from aiogram.filters.callback_data import CallbackData


class ExchangePathsResultCallback(CallbackData, prefix="paths_result"):
    """Payload contract for exchange-path result scene actions."""

    pass

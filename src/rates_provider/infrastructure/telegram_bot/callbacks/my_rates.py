"""CallbackData contracts for my-rates flow actions."""

from aiogram.filters.callback_data import CallbackData


class ListRatesActionCallback(CallbackData, prefix="rates_list"):
    """Payload contract for list-rates scene actions."""

    pass


class RatePairCallback(CallbackData, prefix="rate_pair"):
    """Payload contract for selected currency pair in rates list."""

    source_currency: str
    target_currency: str


class SelectedRateEditCallback(CallbackData, prefix="rate_selected_edit"):
    """Payload contract for selected-rate edit action."""

    pass


class SelectedRateDeleteCallback(CallbackData, prefix="rate_selected_delete"):
    """Payload contract for selected-rate delete action."""

    pass


class DeleteRateConfirmCallback(CallbackData, prefix="rate_delete"):
    """Payload contract for delete confirmation action."""

    pass

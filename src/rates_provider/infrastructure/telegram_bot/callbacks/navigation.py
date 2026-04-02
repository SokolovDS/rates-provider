"""CallbackData contracts for shared navigation and menu actions."""

from aiogram.filters.callback_data import CallbackData


class BackNavigationCallback(CallbackData, prefix="nav"):
    """Payload contract for universal back navigation button."""

    pass


class MainMenuCallback(CallbackData, prefix="main"):
    """Payload contract for main menu actions."""

    pass


class RatesMenuListCallback(CallbackData, prefix="rates_menu_list"):
    """Payload contract for navigating to user's rates list."""

    pass


class RatesMenuFindPathsCallback(CallbackData, prefix="rates_menu_paths"):
    """Payload contract for navigating to exchange paths flow."""

    pass


class RatesMenuCalculateReceivedCallback(CallbackData, prefix="rates_menu_received"):
    """Payload contract for received amount calculation flow."""

    pass


class RatesMenuCalculateRequiredCallback(CallbackData, prefix="rates_menu_required"):
    """Payload contract for required amount calculation flow."""

    pass

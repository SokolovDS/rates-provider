"""Scenes for searching profitable exchange routes in Telegram bot UI."""

from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, ClassVar, cast

from aiogram.fsm.scene import on
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from interfaces.telegram_bot.callbacks.exchange_paths import (
    ExchangePathSourceCurrencyCallback,
    ExchangePathsResultCallback,
    ExchangePathTargetCurrencyCallback,
)
from modules.identity.domain.user import User as InternalUser
from modules.quote_engine.application.compute_exchange_paths import (
    ComputeExchangePathsUseCase,
    ComputeReceivedAmountUseCase,
    ComputeRequiredSourceAmountUseCase,
)
from modules.quote_engine.application.dtos import (
    ComputeExchangePathsCommand,
    ComputeExchangePathsResult,
    ComputeReceivedAmountCommand,
    ComputeReceivedAmountResult,
    ComputeRequiredSourceAmountCommand,
    ComputeRequiredSourceAmountResult,
)
from modules.quote_engine.application.list_selectable_currencies import (
    ListSelectableCurrenciesCommand,
    ListSelectableCurrenciesUseCase,
)
from modules.quote_engine.domain.exceptions import (
    NoExchangePathError,
    NonPositiveAmountError,
)
from modules.user_rates.domain.exceptions import (
    DomainValidationError,
    IdenticalCurrencyPairError,
    InvalidCurrencyCodeError,
)

from .base import BaseTelegramScene, handle_exceptions

SOURCE_CURRENCY_KEY: str = "path_source_currency"
TARGET_CURRENCY_KEY: str = "path_target_currency"
AMOUNT_KEY: str = "path_amount"
RESULT_LINES_KEY: str = "path_result_lines"


def _format_decimal_limited(value: Decimal) -> str:
    """Format Decimal with at most two fractional digits for Telegram output."""
    rounded_value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if rounded_value == rounded_value.to_integral():
        return format(rounded_value.quantize(Decimal("1")), "f")
    return format(rounded_value, "f")


def format_amount_value(amount_value: Decimal) -> str:
    """Format amount value with at most two fractional digits."""
    return _format_decimal_limited(amount_value)


def format_rate_value(rate_value: Decimal) -> str:
    """Format calculated route rate with at most two fractional digits."""
    return _format_decimal_limited(rate_value)


def format_deviation_percent(deviation_percent: Decimal) -> str:
    """Format signed deviation percent relative to best path."""
    if deviation_percent == Decimal("0"):
        return "0%"
    formatted = _format_decimal_limited(deviation_percent)
    if formatted in {"", "-0", "+0"}:
        return "0%"
    return f"{formatted}%"


def build_currency_selection_lines(
    header_lines: list[str],
    prompt_text: str,
    empty_text: str,
    has_choices: bool,
    error_text: str | None = None,
) -> list[str]:
    """Build user-facing lines for a currency selection step."""
    body_text = prompt_text if has_choices else empty_text
    lines = [*header_lines, "", body_text]
    if error_text is not None:
        lines.extend(["", error_text])
    return lines


def build_currency_keyboard_rows(
    currencies: Sequence[str],
    callback_data_builder: Callable[[str], str],
) -> list[list[InlineKeyboardButton]]:
    """Build one inline button row per selectable currency."""
    return [
        [
            InlineKeyboardButton(
                text=currency,
                callback_data=callback_data_builder(currency),
            )
        ]
        for currency in currencies
    ]


def _build_source_currency_callback_data(currency: str) -> str:
    """Build callback payload for selecting a source currency."""
    return ExchangePathSourceCurrencyCallback(currency=currency).pack()


def _build_target_currency_callback_data(currency: str) -> str:
    """Build callback payload for selecting a target currency."""
    return ExchangePathTargetCurrencyCallback(currency=currency).pack()


def build_exchange_paths_lines(result: ComputeExchangePathsResult) -> list[str]:
    """Build user-facing text lines for computed exchange routes."""
    title = f"Маршруты обмена {result.source_currency} -> {result.target_currency}"
    if not result.paths:
        return [title, "", "Маршруты не найдены."]

    lines = [title, ""]
    for path in result.paths:
        route = " -> ".join(path.currencies)
        lines.append(
            f"{route} = {format_rate_value(path.effective_rate)} "
            f"({format_deviation_percent(path.deviation_percent)})"
        )
    return lines


def build_received_amount_lines(result: ComputeReceivedAmountResult) -> list[str]:
    """Build user-facing lines for target amount received per route."""
    title = (
        f"Получишь за {format_amount_value(result.source_amount)} "
        f"{result.source_currency} -> {result.target_currency}"
    )
    if not result.paths:
        return [title, "", "Маршруты не найдены."]

    lines = [title, ""]
    for path in result.paths:
        route = " -> ".join(path.currencies)
        lines.append(
            f"{route} = {format_amount_value(path.target_amount)} {result.target_currency} "
            f"(курс: {format_rate_value(path.effective_rate)}, "
            f"{format_deviation_percent(path.deviation_percent)})"
        )
    return lines


def build_required_source_amount_lines(
    result: ComputeRequiredSourceAmountResult,
) -> list[str]:
    """Build user-facing lines for source amount required per route."""
    title = (
        f"Нужно для получения {format_amount_value(result.target_amount)} "
        f"{result.target_currency} из {result.source_currency}"
    )
    if not result.paths:
        return [title, "", "Маршруты не найдены."]

    lines = [title, ""]
    for path in result.paths:
        route = " -> ".join(path.currencies)
        lines.append(
            f"{route} = {format_amount_value(path.source_amount)} {result.source_currency} "
            f"(курс: {format_rate_value(path.effective_rate)}, "
            f"{format_deviation_percent(path.deviation_percent)})"
        )
    return lines


def _path_error_message(error: Exception) -> str:
    """Map path-search errors to user-friendly Russian text."""
    if isinstance(error, InvalidCurrencyCodeError):
        return "Ошибка: валюта должна быть из 3 латинских букв, например USD."
    if isinstance(error, IdenticalCurrencyPairError):
        return "Ошибка: исходная и целевая валюты должны отличаться."
    if isinstance(error, NoExchangePathError):
        return "Ошибка: не найдено ни одного маршрута для указанной пары валют."
    if isinstance(error, (InvalidOperation, NonPositiveAmountError)):
        return "Ошибка: сумма должна быть положительным числом, например 100 или 100.50."
    return "Ошибка: не удалось рассчитать маршруты обмена."


def _parse_amount(value: str) -> Decimal:
    """Parse numeric amount from user text."""
    return Decimal(value.strip())


class _ExchangeResultScene(BaseTelegramScene):
    """Base result scene with reusable rendering and explicit menu action."""

    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = [
        InlineKeyboardButton(
            text="В меню", callback_data=ExchangePathsResultCallback().pack()
        )
    ]

    async def _create_base_lines(self) -> list[str]:
        """Read precomputed result lines from scene data."""
        data = await self.wizard.get_data()
        raw_lines = data.get(RESULT_LINES_KEY)
        if isinstance(raw_lines, list):
            object_lines = cast(list[object], raw_lines)
            typed_lines = [
                line for line in object_lines if isinstance(line, str)]
            if len(typed_lines) == len(object_lines):
                return typed_lines
        return ["Результат", "", "Не удалось отобразить результат."]

    @on.callback_query(ExchangePathsResultCallback.filter())
    async def on_menu_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Open rates menu as a fresh message and preserve result output above."""
        await callback_query.answer()
        await self.collapse_to("rates_menu", fresh_ui_message=True)


class _CurrencySelectionScene(BaseTelegramScene):
    """Base scene for rendering currency selection keyboards with shared layout."""

    async def _selection_payload(
        self,
        *,
        header_lines: list[str],
        prompt_text: str,
        empty_text: str,
        currencies: Sequence[str],
        callback_data_builder: Callable[[str], str],
        error_text: str | None = None,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and inline keyboard payload for a currency selection step."""
        text_lines = build_currency_selection_lines(
            header_lines=header_lines,
            prompt_text=prompt_text,
            empty_text=empty_text,
            has_choices=bool(currencies),
            error_text=error_text,
        )
        rows = build_currency_keyboard_rows(currencies, callback_data_builder)
        markup = await self._build_markup(rows)
        return "\n".join(text_lines), markup


class ExchangePathSourceScene(_CurrencySelectionScene, state="exchange_paths:source"):
    """Step 1 scene that asks source currency for path lookup."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/2. Выбери исходную валюту."
    _EMPTY_TEXT: ClassVar[str] = "Нет доступных валют для поиска маршрутов."

    async def _create_base_lines(self) -> list[str]:
        """Create source-currency header lines."""
        return ["Поиск маршрутов обмена"]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build source-currency selection payload with available codes."""
        list_selectable_currencies_use_case = cast(
            ListSelectableCurrenciesUseCase,
            kwargs["list_selectable_currencies_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        result = await list_selectable_currencies_use_case.execute(
            ListSelectableCurrenciesCommand(user_id=current_user.user_id.value)
        )
        return await self._selection_payload(
            header_lines=await self._create_base_lines(),
            prompt_text=self._PROMPT_TEXT,
            empty_text=self._EMPTY_TEXT,
            currencies=result.currencies,
            callback_data_builder=_build_source_currency_callback_data,
        )

    @on.callback_query(ExchangePathSourceCurrencyCallback.filter())
    async def on_source_currency_click(
        self,
        callback_query: CallbackQuery,
        callback_data: ExchangePathSourceCurrencyCallback,
    ) -> None:
        """Save selected source currency and move to target step."""
        await callback_query.answer()
        source_currency = callback_data.currency
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(ExchangePathTargetScene)


class ExchangePathTargetScene(_CurrencySelectionScene, state="exchange_paths:target"):
    """Step 2 scene that asks target currency and computes routes."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/2. Выбери целевую валюту."
    _EMPTY_TEXT: ClassVar[str] = (
        "Нет доступных целевых валют для выбранной исходной."
    )

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency header lines with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Поиск маршрутов обмена",
            f"Исходная валюта: {source_currency}",
        ]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build target-currency selection payload with reachable currencies."""
        list_selectable_currencies_use_case = cast(
            ListSelectableCurrenciesUseCase,
            kwargs["list_selectable_currencies_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        result = await list_selectable_currencies_use_case.execute(
            ListSelectableCurrenciesCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
            )
        )
        return await self._selection_payload(
            header_lines=await self._create_base_lines(),
            prompt_text=self._PROMPT_TEXT,
            empty_text=self._EMPTY_TEXT,
            currencies=result.currencies,
            callback_data_builder=_build_target_currency_callback_data,
        )

    @on.callback_query(ExchangePathTargetCurrencyCallback.filter())
    async def on_target_currency_click(
        self,
        callback_query: CallbackQuery,
        callback_data: ExchangePathTargetCurrencyCallback,
        compute_exchange_paths_use_case: ComputeExchangePathsUseCase,
        list_selectable_currencies_use_case: ListSelectableCurrenciesUseCase,
        current_user: InternalUser,
    ) -> None:
        """Compute routes for selected source/target pair and move to result screen."""
        await callback_query.answer()
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        target_currency = callback_data.currency
        await self.wizard.update_data({TARGET_CURRENCY_KEY: target_currency})
        try:
            result = await compute_exchange_paths_use_case.execute(
                ComputeExchangePathsCommand(
                    user_id=current_user.user_id.value,
                    source_currency=source_currency,
                    target_currency=target_currency,
                )
            )
        except (DomainValidationError, NoExchangePathError, InvalidCurrencyCodeError) as error:
            selectable_result = await list_selectable_currencies_use_case.execute(
                ListSelectableCurrenciesCommand(
                    user_id=current_user.user_id.value,
                    source_currency=source_currency,
                )
            )
            message = callback_query.message
            if isinstance(message, Message):
                text, reply_markup = await self._selection_payload(
                    header_lines=await self._create_base_lines(),
                    prompt_text=self._PROMPT_TEXT,
                    empty_text=self._EMPTY_TEXT,
                    currencies=selectable_result.currencies,
                    callback_data_builder=_build_target_currency_callback_data,
                    error_text=_path_error_message(error),
                )
                await message.edit_text(text, reply_markup=reply_markup)
            return
        await self.wizard.update_data({RESULT_LINES_KEY: build_exchange_paths_lines(result)})
        await self.wizard.goto(ExchangePathResultScene)


class ExchangePathResultScene(_ExchangeResultScene, state="exchange_paths:result"):
    """Result screen for exchange path discovery."""


class ReceivedAmountSourceScene(_CurrencySelectionScene, state="exchange_paths:received_source"):
    """Step 1 scene that asks source currency for received-amount calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/3. Выбери исходную валюту."
    _EMPTY_TEXT: ClassVar[str] = "Нет доступных валют для расчёта суммы."

    async def _create_base_lines(self) -> list[str]:
        """Create header lines for received-amount source selection."""
        return ["Сколько получишь за сумму"]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build source-currency selection payload for received-amount flow."""
        list_selectable_currencies_use_case = cast(
            ListSelectableCurrenciesUseCase,
            kwargs["list_selectable_currencies_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        result = await list_selectable_currencies_use_case.execute(
            ListSelectableCurrenciesCommand(user_id=current_user.user_id.value)
        )
        return await self._selection_payload(
            header_lines=await self._create_base_lines(),
            prompt_text=self._PROMPT_TEXT,
            empty_text=self._EMPTY_TEXT,
            currencies=result.currencies,
            callback_data_builder=_build_source_currency_callback_data,
        )

    @on.callback_query(ExchangePathSourceCurrencyCallback.filter())
    async def on_source_currency_click(
        self,
        callback_query: CallbackQuery,
        callback_data: ExchangePathSourceCurrencyCallback,
    ) -> None:
        """Save selected source currency and move to target step."""
        await callback_query.answer()
        source_currency = callback_data.currency
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(ReceivedAmountTargetScene)


class ReceivedAmountTargetScene(_CurrencySelectionScene, state="exchange_paths:received_target"):
    """Step 2 scene that asks target currency for received-amount calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/3. Выбери целевую валюту."
    _EMPTY_TEXT: ClassVar[str] = (
        "Нет доступных целевых валют для выбранной исходной."
    )

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency header lines with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Сколько получишь за сумму",
            f"Исходная валюта: {source_currency}",
        ]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build target-currency selection payload for received-amount flow."""
        list_selectable_currencies_use_case = cast(
            ListSelectableCurrenciesUseCase,
            kwargs["list_selectable_currencies_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        result = await list_selectable_currencies_use_case.execute(
            ListSelectableCurrenciesCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
            )
        )
        return await self._selection_payload(
            header_lines=await self._create_base_lines(),
            prompt_text=self._PROMPT_TEXT,
            empty_text=self._EMPTY_TEXT,
            currencies=result.currencies,
            callback_data_builder=_build_target_currency_callback_data,
        )

    @on.callback_query(ExchangePathTargetCurrencyCallback.filter())
    async def on_target_currency_click(
        self,
        callback_query: CallbackQuery,
        callback_data: ExchangePathTargetCurrencyCallback,
    ) -> None:
        """Save selected target currency and move to amount step."""
        await callback_query.answer()
        target_currency = callback_data.currency
        await self.wizard.update_data({TARGET_CURRENCY_KEY: target_currency})
        await self.wizard.goto(ReceivedAmountValueScene)


class ReceivedAmountValueScene(BaseTelegramScene, state="exchange_paths:received_value"):
    """Step 3 scene that asks source amount and computes target results."""

    _PROMPT_TEXT: ClassVar[
        str] = "Шаг 3/3. Введи сумму исходной валюты (например 100 или 100.50)."

    async def _create_base_lines(self) -> list[str]:
        """Create amount prompt text with source and target context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, "-"))
        return [
            "Сколько получишь за сумму",
            f"Исходная валюта: {source_currency}",
            f"Целевая валюта: {target_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_path_error_message, InvalidOperation, DomainValidationError)
    async def on_amount(
        self,
        message: Message,
        compute_received_amount_use_case: ComputeReceivedAmountUseCase,
        current_user: InternalUser,
    ) -> None:
        """Compute target amount for entered source amount and return to menu."""
        await self._best_effort_delete_user_message(message)
        source_amount = _parse_amount(message.text or "")
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, ""))
        result = await compute_received_amount_use_case.execute(
            ComputeReceivedAmountCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
                target_currency=target_currency,
                source_amount=source_amount,
            )
        )
        await self.wizard.update_data({RESULT_LINES_KEY: build_received_amount_lines(result)})
        await self.wizard.goto(ReceivedAmountResultScene)


class ReceivedAmountResultScene(_ExchangeResultScene, state="exchange_paths:received_result"):
    """Result screen for received-amount calculation."""


class RequiredAmountSourceScene(_CurrencySelectionScene, state="exchange_paths:required_source"):
    """Step 1 scene that asks source currency for required-source calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/3. Выбери исходную валюту."
    _EMPTY_TEXT: ClassVar[str] = "Нет доступных валют для расчёта исходной суммы."

    async def _create_base_lines(self) -> list[str]:
        """Create header lines for required-source source selection."""
        return ["Сколько нужно исходной валюты"]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build source-currency selection payload for required-source flow."""
        list_selectable_currencies_use_case = cast(
            ListSelectableCurrenciesUseCase,
            kwargs["list_selectable_currencies_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        result = await list_selectable_currencies_use_case.execute(
            ListSelectableCurrenciesCommand(user_id=current_user.user_id.value)
        )
        return await self._selection_payload(
            header_lines=await self._create_base_lines(),
            prompt_text=self._PROMPT_TEXT,
            empty_text=self._EMPTY_TEXT,
            currencies=result.currencies,
            callback_data_builder=_build_source_currency_callback_data,
        )

    @on.callback_query(ExchangePathSourceCurrencyCallback.filter())
    async def on_source_currency_click(
        self,
        callback_query: CallbackQuery,
        callback_data: ExchangePathSourceCurrencyCallback,
    ) -> None:
        """Save selected source currency and move to target step."""
        await callback_query.answer()
        source_currency = callback_data.currency
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(RequiredAmountTargetScene)


class RequiredAmountTargetScene(_CurrencySelectionScene, state="exchange_paths:required_target"):
    """Step 2 scene that asks target currency for required-source calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/3. Выбери целевую валюту."
    _EMPTY_TEXT: ClassVar[str] = (
        "Нет доступных целевых валют для выбранной исходной."
    )

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency header lines with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Сколько нужно исходной валюты",
            f"Исходная валюта: {source_currency}",
        ]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build target-currency selection payload for required-source flow."""
        list_selectable_currencies_use_case = cast(
            ListSelectableCurrenciesUseCase,
            kwargs["list_selectable_currencies_use_case"],
        )
        current_user = cast(InternalUser, kwargs["current_user"])
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        result = await list_selectable_currencies_use_case.execute(
            ListSelectableCurrenciesCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
            )
        )
        return await self._selection_payload(
            header_lines=await self._create_base_lines(),
            prompt_text=self._PROMPT_TEXT,
            empty_text=self._EMPTY_TEXT,
            currencies=result.currencies,
            callback_data_builder=_build_target_currency_callback_data,
        )

    @on.callback_query(ExchangePathTargetCurrencyCallback.filter())
    async def on_target_currency_click(
        self,
        callback_query: CallbackQuery,
        callback_data: ExchangePathTargetCurrencyCallback,
    ) -> None:
        """Save selected target currency and move to amount step."""
        await callback_query.answer()
        target_currency = callback_data.currency
        await self.wizard.update_data({TARGET_CURRENCY_KEY: target_currency})
        await self.wizard.goto(RequiredAmountValueScene)


class RequiredAmountValueScene(BaseTelegramScene, state="exchange_paths:required_value"):
    """Step 3 scene that asks target amount and computes source requirements."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 3/3. Введи сумму целевой валюты (например 100 или 100.50)."

    async def _create_base_lines(self) -> list[str]:
        """Create amount prompt text with source and target context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, "-"))
        return [
            "Сколько нужно исходной валюты",
            f"Исходная валюта: {source_currency}",
            f"Целевая валюта: {target_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_path_error_message, InvalidOperation, DomainValidationError)
    async def on_amount(
        self,
        message: Message,
        compute_required_source_amount_use_case: ComputeRequiredSourceAmountUseCase,
        current_user: InternalUser,
    ) -> None:
        """Compute required source amount for entered target amount and return to menu."""
        await self._best_effort_delete_user_message(message)
        target_amount = _parse_amount(message.text or "")
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, ""))
        result = await compute_required_source_amount_use_case.execute(
            ComputeRequiredSourceAmountCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
                target_currency=target_currency,
                target_amount=target_amount,
            )
        )
        await self.wizard.update_data(
            {RESULT_LINES_KEY: build_required_source_amount_lines(result)}
        )
        await self.wizard.goto(RequiredAmountResultScene)


class RequiredAmountResultScene(_ExchangeResultScene, state="exchange_paths:required_result"):
    """Result screen for required-source amount calculation."""

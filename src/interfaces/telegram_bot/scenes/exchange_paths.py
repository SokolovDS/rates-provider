"""Scenes for searching profitable exchange routes in Telegram bot UI."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import ClassVar, cast

from aiogram.fsm.scene import on
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from app.shared._validation import normalize_currency_code
from interfaces.telegram_bot.callbacks.exchange_paths import (
    ExchangePathsResultCallback,
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
        if isinstance(raw_lines, list) and all(
            isinstance(line, str) for line in raw_lines
        ):
            return cast(list[str], list(raw_lines))
        return ["Результат", "", "Не удалось отобразить результат."]

    @on.callback_query(ExchangePathsResultCallback.filter())
    async def on_menu_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Open rates menu as a fresh message and preserve result output above."""
        await callback_query.answer()
        await self.collapse_to("rates_menu", fresh_ui_message=True)


class ExchangePathSourceScene(BaseTelegramScene, state="exchange_paths:source"):
    """Step 1 scene that asks source currency for path lookup."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/2. Введи исходную валюту (например RUB)."

    async def _create_base_lines(self) -> list[str]:
        """Create source-currency prompt text lines."""
        return ["Поиск маршрутов обмена", "", self._PROMPT_TEXT]

    @on.message()
    @handle_exceptions(_path_error_message, DomainValidationError)
    async def on_source_currency(self, message: Message) -> None:
        """Validate source currency and move to target step."""
        await self._best_effort_delete_user_message(message)
        source_currency = normalize_currency_code(message.text or "")
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(ExchangePathTargetScene)


class ExchangePathTargetScene(BaseTelegramScene, state="exchange_paths:target"):
    """Step 2 scene that asks target currency and computes routes."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/2. Введи целевую валюту (например THB)."

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency prompt text lines with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Поиск маршрутов обмена",
            f"Исходная валюта: {source_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_path_error_message, DomainValidationError)
    async def on_target_currency(
        self,
        message: Message,
        compute_exchange_paths_use_case: ComputeExchangePathsUseCase,
        current_user: InternalUser,
    ) -> None:
        """Compute routes for source/target pair and move to result screen."""
        await self._best_effort_delete_user_message(message)
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        target_currency = normalize_currency_code(message.text or "")
        await self.wizard.update_data({TARGET_CURRENCY_KEY: target_currency})

        result = await compute_exchange_paths_use_case.execute(
            ComputeExchangePathsCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
                target_currency=target_currency,
            )
        )
        await self.wizard.update_data({RESULT_LINES_KEY: build_exchange_paths_lines(result)})
        await self.wizard.goto(ExchangePathResultScene)


class ExchangePathResultScene(_ExchangeResultScene, state="exchange_paths:result"):
    """Result screen for exchange path discovery."""


class ReceivedAmountSourceScene(BaseTelegramScene, state="exchange_paths:received_source"):
    """Step 1 scene that asks source currency for received-amount calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/3. Введи исходную валюту (например RUB)."

    async def _create_base_lines(self) -> list[str]:
        """Create prompt text for received-amount source input."""
        return ["Сколько получишь за сумму", "", self._PROMPT_TEXT]

    @on.message()
    @handle_exceptions(_path_error_message, DomainValidationError)
    async def on_source_currency(self, message: Message) -> None:
        """Validate source currency and move to target step."""
        await self._best_effort_delete_user_message(message)
        source_currency = normalize_currency_code(message.text or "")
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(ReceivedAmountTargetScene)


class ReceivedAmountTargetScene(BaseTelegramScene, state="exchange_paths:received_target"):
    """Step 2 scene that asks target currency for received-amount calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/3. Введи целевую валюту (например THB)."

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency prompt text with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Сколько получишь за сумму",
            f"Исходная валюта: {source_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_path_error_message, DomainValidationError)
    async def on_target_currency(self, message: Message) -> None:
        """Validate target currency and move to amount step."""
        await self._best_effort_delete_user_message(message)
        target_currency = normalize_currency_code(message.text or "")
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        if target_currency == source_currency:
            raise IdenticalCurrencyPairError(
                "Exchange-route currencies must differ.")
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


class RequiredAmountSourceScene(BaseTelegramScene, state="exchange_paths:required_source"):
    """Step 1 scene that asks source currency for required-source calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/3. Введи исходную валюту (например RUB)."

    async def _create_base_lines(self) -> list[str]:
        """Create prompt text for required-source source input."""
        return ["Сколько нужно исходной валюты", "", self._PROMPT_TEXT]

    @on.message()
    @handle_exceptions(_path_error_message, DomainValidationError)
    async def on_source_currency(self, message: Message) -> None:
        """Validate source currency and move to target step."""
        await self._best_effort_delete_user_message(message)
        source_currency = normalize_currency_code(message.text or "")
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(RequiredAmountTargetScene)


class RequiredAmountTargetScene(BaseTelegramScene, state="exchange_paths:required_target"):
    """Step 2 scene that asks target currency for required-source calculation."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/3. Введи целевую валюту (например THB)."

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency prompt text with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Сколько нужно исходной валюты",
            f"Исходная валюта: {source_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_path_error_message, DomainValidationError)
    async def on_target_currency(self, message: Message) -> None:
        """Validate target currency and move to amount step."""
        await self._best_effort_delete_user_message(message)
        target_currency = normalize_currency_code(message.text or "")
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        if target_currency == source_currency:
            raise IdenticalCurrencyPairError(
                "Exchange-route currencies must differ.")
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

"""Add-rate scene for Telegram bot UI."""

from decimal import InvalidOperation
from typing import ClassVar

from aiogram.fsm.scene import on
from aiogram.types import Message

from rates_provider.application._validation import normalize_currency_code
from rates_provider.application.add_exchange_rate import (
    AddExchangeRateCommand,
    AddExchangeRateUseCase,
)
from rates_provider.domain.exceptions import (
    DomainValidationError,
    IdenticalCurrencyPairError,
    InvalidCurrencyCodeError,
    NonPositiveRateValueError,
)
from users_service.domain.user import User as InternalUser

from ..base import BaseTelegramScene, handle_exceptions
from ..shared.formatting import format_rate_value_plain, parse_rate_value
from ..shared.state_keys import SOURCE_CURRENCY_KEY, TARGET_CURRENCY_KEY


def _domain_error_message(error: Exception) -> str:
    """Map domain validation errors to user-friendly Russian text."""
    if isinstance(error, InvalidCurrencyCodeError):
        return "Ошибка: валюта должна быть из 3 латинских букв, например USD."
    if isinstance(error, IdenticalCurrencyPairError):
        return "Ошибка: целевая валюта должна отличаться от исходной."
    if isinstance(error, (InvalidOperation, NonPositiveRateValueError)):
        return "Ошибка: курс должен быть положительным числом, например 90.50."
    return "Ошибка: не удалось сохранить курс. Проверьте введенные данные."


class AddRateSourceScene(BaseTelegramScene, state="add_rate:source"):
    """Step 1 scene that asks the source currency."""

    _TEXT_LINES: ClassVar[list[str]] = ["Добавление курса", ""]
    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/3. Введи исходную валюту (например USD)."

    @on.message()
    async def on_source_currency(self, message: Message) -> None:
        """Validate source currency and move to target step."""
        await self._best_effort_delete_user_message(message)
        source_currency = normalize_currency_code(message.text or "")
        await self.wizard.update_data({SOURCE_CURRENCY_KEY: source_currency})
        await self.wizard.goto(AddRateTargetScene)


class AddRateTargetScene(BaseTelegramScene, state="add_rate:target"):
    """Step 2 scene that asks the target currency."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 2/3. Введи целевую валюту (например EUR)."

    async def _create_base_lines(self) -> list[str]:
        """Create target-currency prompt base text lines with source context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        return [
            "Добавление курса",
            f"Исходная валюта: {source_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_domain_error_message, DomainValidationError)
    async def on_target_currency(self, message: Message) -> None:
        """Validate target currency and move to rate step."""
        await self._best_effort_delete_user_message(message)
        target_currency = normalize_currency_code(message.text or "")

        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        if target_currency == source_currency:
            raise IdenticalCurrencyPairError(
                "Exchange-rate currencies must differ.")

        await self.wizard.update_data({TARGET_CURRENCY_KEY: target_currency})
        await self.wizard.goto(AddRateValueScene)


class AddRateValueScene(BaseTelegramScene, state="add_rate:value"):
    """Step 3 scene that asks the exchange-rate numeric value."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 3/3. Введи курс (например 90.50)."

    async def _create_base_lines(self) -> list[str]:
        """Create rate prompt base text lines with source and target context."""
        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, "-"))
        return [
            "Добавление курса",
            f"Исходная валюта: {source_currency}",
            f"Целевая валюта: {target_currency}",
            "",
            self._PROMPT_TEXT,
        ]

    @on.message()
    @handle_exceptions(_domain_error_message, InvalidOperation, DomainValidationError)
    async def on_rate_value(
        self,
        message: Message,
        add_exchange_rate_use_case: AddExchangeRateUseCase,
        current_user: InternalUser,
    ) -> None:
        """Accept and validate rate value, then return to rates menu scene."""
        await self._best_effort_delete_user_message(message)
        rate_value = parse_rate_value(message.text or "")

        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, "-"))

        result = await add_exchange_rate_use_case.execute(
            AddExchangeRateCommand(
                user_id=current_user.user_id.value,
                source_currency=source_currency,
                target_currency=target_currency,
                rate_value=rate_value,
            )
        )

        success_text = (
            "Курс принят:\n"
            f"{result.source_currency} -> {result.target_currency} = "
            f"{format_rate_value_plain(result.rate_value)}"
        )

        await self._render_for_message(message, success_text, None)
        await self.collapse_to("rates_list", fresh_ui_message=True)

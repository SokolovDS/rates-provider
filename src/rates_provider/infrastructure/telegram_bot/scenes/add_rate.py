"""Add-rate scene for Telegram bot UI."""

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.scene import on
from aiogram.types import (
    CallbackQuery,
    Message,
)

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
from rates_provider.domain.exchange_rate import CurrencyCode
from users_service.domain.user import User as InternalUser

from .base import BaseTelegramScene, handle_exceptions

UI_MESSAGE_ID_KEY: str = "ui_message_id"
SOURCE_CURRENCY_KEY: str = "source_currency"
TARGET_CURRENCY_KEY: str = "target_currency"


def _parse_rate(value: str) -> Decimal:
    """Parse decimal input value from user text."""
    return Decimal(value.strip())


def _format_rate_value(rate_value: Decimal) -> str:
    """Format Decimal rate without scientific notation."""
    return format(rate_value, "f")


def _domain_error_message(error: Exception) -> str:
    """Map domain validation errors to user-friendly Russian text."""
    if isinstance(error, InvalidCurrencyCodeError):
        return "Ошибка: валюта должна быть из 3 латинских букв, например USD."
    if isinstance(error, IdenticalCurrencyPairError):
        return "Ошибка: целевая валюта должна отличаться от исходной."
    if isinstance(error, (InvalidOperation, NonPositiveRateValueError)):
        return "Ошибка: курс должен быть положительным числом, например 90.50."
    return "Ошибка: не удалось сохранить курс. Проверьте введенные данные."


async def _best_effort_delete_user_message(message: Message) -> None:
    """Delete user message if possible, but keep flow alive on failure."""
    try:
        await message.delete()
    except TelegramAPIError:
        return


class AddRateSourceScene(BaseTelegramScene, state="add_rate:source"):
    """Step 1 scene that asks the source currency."""

    _PROMPT_TEXT: ClassVar[str] = "Шаг 1/3. Введи исходную валюту (например USD)."

    async def _create_base_lines(self) -> list[str]:
        """Create source-currency prompt base text lines."""
        return ["Добавление курса", "", self._PROMPT_TEXT]

    @on.message.enter()
    async def on_enter_from_message(self, message: Message) -> None:
        """Render source-currency prompt when entered from a message event."""
        text, reply_markup = await self._payload()
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(self, callback_query: CallbackQuery) -> None:
        """Render source-currency prompt by editing current UI message."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._payload()
        await message.edit_text(text, reply_markup=reply_markup)
        await self.wizard.update_data({UI_MESSAGE_ID_KEY: message.message_id})

    @on.message()
    @handle_exceptions(_domain_error_message, DomainValidationError)
    async def on_source_currency(self, message: Message) -> None:
        """Accept and validate source currency, then move to target step."""
        await _best_effort_delete_user_message(message)
        source_currency = CurrencyCode(message.text or "").value

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

    @on.message.enter()
    async def on_enter_from_message(self, message: Message) -> None:
        """Render target-currency prompt when entered from a message event."""
        text, reply_markup = await self._payload()
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(self, callback_query: CallbackQuery) -> None:
        """Render target-currency prompt by editing current UI message."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._payload()
        await message.edit_text(text, reply_markup=reply_markup)
        await self.wizard.update_data({UI_MESSAGE_ID_KEY: message.message_id})

    @on.message()
    @handle_exceptions(_domain_error_message, DomainValidationError)
    async def on_target_currency(self, message: Message) -> None:
        """Accept and validate target currency, then move to rate step."""
        await _best_effort_delete_user_message(message)
        text_input = message.text or ""
        target_currency = CurrencyCode(text_input).value

        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, ""))
        if target_currency == source_currency:
            raise IdenticalCurrencyPairError(
                "Exchange-rate currencies must differ."
            )

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

    @on.message.enter()
    async def on_enter_from_message(self, message: Message) -> None:
        """Render rate prompt when entered from a message event."""
        text, reply_markup = await self._payload()
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(self, callback_query: CallbackQuery) -> None:
        """Render rate prompt by editing current UI message."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._payload()
        await message.edit_text(text, reply_markup=reply_markup)
        await self.wizard.update_data({UI_MESSAGE_ID_KEY: message.message_id})

    @on.message()
    @handle_exceptions(_domain_error_message, InvalidOperation, DomainValidationError)
    async def on_rate_value(
        self,
        message: Message,
        add_exchange_rate_use_case: AddExchangeRateUseCase,
        current_user: InternalUser,
    ) -> None:
        """Accept and validate rate value, then return to main menu scene."""
        await _best_effort_delete_user_message(message)
        rate_value = _parse_rate(message.text or "")

        data = await self.wizard.get_data()
        source_currency = str(data.get(SOURCE_CURRENCY_KEY, "-"))
        target_currency = str(data.get(TARGET_CURRENCY_KEY, "-"))
        ui_message_id = data.get(UI_MESSAGE_ID_KEY)
        bot = message.bot

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
            f"{_format_rate_value(result.rate_value)}"
        )

        if isinstance(ui_message_id, int) and bot is not None:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=ui_message_id,
                    text=success_text,
                )
            except TelegramBadRequest:
                await message.answer(success_text)
        else:
            await message.answer(success_text)

        await self.collapse_to("rates_menu")

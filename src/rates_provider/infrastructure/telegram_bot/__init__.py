"""Telegram bot package entrypoint and dispatcher wiring."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.scene import SceneRegistry

from rates_provider.application.add_exchange_rate import AddExchangeRateUseCase
from rates_provider.application.compute_exchange_paths import (
    ComputeExchangePathsUseCase,
    ComputeReceivedAmountUseCase,
    ComputeRequiredSourceAmountUseCase,
)
from rates_provider.application.delete_exchange_rate import DeleteExchangeRateUseCase
from rates_provider.application.list_exchange_rates import ListExchangeRatesUseCase
from rates_provider.application.update_exchange_rate import UpdateExchangeRateUseCase
from rates_provider.infrastructure.repository_factory import (
    build_exchange_rate_repository,
    build_user_repository,
)
from users_service.application.resolve_or_create_telegram_user import (
    ResolveOrCreateTelegramUserUseCase,
)
from users_service.infrastructure.telegram.ensure_user import EnsureTelegramUserMiddleware

from .scenes.exchange_paths import (
    ExchangePathResultScene,
    ExchangePathSourceScene,
    ExchangePathTargetScene,
    ReceivedAmountResultScene,
    ReceivedAmountSourceScene,
    ReceivedAmountTargetScene,
    ReceivedAmountValueScene,
    RequiredAmountResultScene,
    RequiredAmountSourceScene,
    RequiredAmountTargetScene,
    RequiredAmountValueScene,
)
from .scenes.main_menu import MainMenuScene
from .scenes.my_rates.add_rate import (
    AddRateSourceScene,
    AddRateTargetScene,
    AddRateValueScene,
)
from .scenes.my_rates.delete_rate_confirm import DeleteRateConfirmScene
from .scenes.my_rates.edit_rate import EditRateValueScene
from .scenes.my_rates.list_rates import ListRatesScene
from .scenes.my_rates.selected_rate import SelectedRateScene
from .scenes.rates_menu import RatesMenuScene

__all__ = ["run_bot"]


def build_router() -> Router:
    """Build root router and route /start into MainMenuScene."""
    router = Router()
    router.message.register(MainMenuScene.as_handler(), CommandStart())
    return router


async def run_bot(token: str) -> None:
    """Run Telegram bot with configured application services."""
    logging.basicConfig(level=logging.INFO)

    repository = build_exchange_rate_repository()
    user_repository = build_user_repository()
    add_exchange_rate_use_case = AddExchangeRateUseCase(repository)
    update_exchange_rate_use_case = UpdateExchangeRateUseCase(repository)
    delete_exchange_rate_use_case = DeleteExchangeRateUseCase(repository)
    list_exchange_rates_use_case = ListExchangeRatesUseCase(repository)
    compute_exchange_paths_use_case = ComputeExchangePathsUseCase(repository)
    compute_received_amount_use_case = ComputeReceivedAmountUseCase(repository)
    compute_required_source_amount_use_case = ComputeRequiredSourceAmountUseCase(
        repository)
    resolve_or_create_user_use_case = ResolveOrCreateTelegramUserUseCase(
        user_repository)

    bot = Bot(token=token, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(
        EnsureTelegramUserMiddleware(resolve_or_create_user_use_case))
    dp.workflow_data["add_exchange_rate_use_case"] = add_exchange_rate_use_case
    dp.workflow_data["update_exchange_rate_use_case"] = update_exchange_rate_use_case
    dp.workflow_data["delete_exchange_rate_use_case"] = delete_exchange_rate_use_case
    dp.workflow_data["list_exchange_rates_use_case"] = list_exchange_rates_use_case
    dp.workflow_data["compute_exchange_paths_use_case"] = compute_exchange_paths_use_case
    dp.workflow_data["compute_received_amount_use_case"] = compute_received_amount_use_case
    dp.workflow_data["compute_required_source_amount_use_case"] = (
        compute_required_source_amount_use_case
    )
    dp.workflow_data["resolve_or_create_user_use_case"] = resolve_or_create_user_use_case
    dp.include_router(build_router())

    registry = SceneRegistry(dp)
    registry.add(
        MainMenuScene,
        RatesMenuScene,
        ListRatesScene,
        SelectedRateScene,
        ExchangePathSourceScene,
        ExchangePathTargetScene,
        ExchangePathResultScene,
        ReceivedAmountSourceScene,
        ReceivedAmountTargetScene,
        ReceivedAmountValueScene,
        ReceivedAmountResultScene,
        RequiredAmountSourceScene,
        RequiredAmountTargetScene,
        RequiredAmountValueScene,
        RequiredAmountResultScene,
        AddRateSourceScene,
        AddRateTargetScene,
        AddRateValueScene,
        EditRateValueScene,
        DeleteRateConfirmScene,
    )

    await dp.start_polling(bot)

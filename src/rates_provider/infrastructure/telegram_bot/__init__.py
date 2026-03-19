"""Telegram bot package entrypoint and dispatcher wiring."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.scene import SceneRegistry

from rates_provider.application.add_exchange_rate import AddExchangeRateUseCase
from rates_provider.application.list_exchange_rates import ListExchangeRatesUseCase
from rates_provider.infrastructure.repository_factory import (
    build_exchange_rate_repository,
    build_user_repository,
)
from users_service.application.resolve_or_create_telegram_user import (
    ResolveOrCreateTelegramUserUseCase,
)
from users_service.infrastructure.telegram.ensure_user import EnsureTelegramUserMiddleware

from .scenes.add_rate import AddRateSourceScene, AddRateTargetScene, AddRateValueScene
from .scenes.list_rates import ListRatesScene
from .scenes.main_menu import MainMenuScene
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
    list_exchange_rates_use_case = ListExchangeRatesUseCase(repository)
    resolve_or_create_user_use_case = ResolveOrCreateTelegramUserUseCase(
        user_repository)

    bot = Bot(token=token, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(
        EnsureTelegramUserMiddleware(resolve_or_create_user_use_case))
    dp.workflow_data["add_exchange_rate_use_case"] = add_exchange_rate_use_case
    dp.workflow_data["list_exchange_rates_use_case"] = list_exchange_rates_use_case
    dp.workflow_data["resolve_or_create_user_use_case"] = resolve_or_create_user_use_case
    dp.include_router(build_router())

    registry = SceneRegistry(dp)
    registry.add(
        MainMenuScene,
        RatesMenuScene,
        ListRatesScene,
        AddRateSourceScene,
        AddRateTargetScene,
        AddRateValueScene,
    )

    await dp.start_polling(bot)

"""Scene for displaying market exchange rates in Telegram bot UI."""

from typing import Any, ClassVar, cast

from aiogram.types import InlineKeyboardMarkup

from interfaces.telegram_bot.scenes.shared.formatting import format_rate_value_plain
from modules.market_rates.application.list_market_rates import (
    ListMarketRatesResult,
    ListMarketRatesUseCase,
)

from .base import BaseTelegramScene


def _build_market_rates_lines(
    result: ListMarketRatesResult,
    text_lines: list[str],
) -> list[str]:
    """Build text lines for the market-rates display scene, grouped by source currency."""
    if not result.exchange_rates:
        return [*text_lines, "", "Данные отсутствуют."]

    sorted_entries = sorted(
        result.exchange_rates,
        key=lambda e: (e.source_currency, e.target_currency),
    )

    lines: list[str] = list(text_lines)
    current_source: str | None = None
    for entry in sorted_entries:
        if entry.source_currency != current_source:
            current_source = entry.source_currency
            lines.append("")
            lines.append(f"<b>1 {current_source}</b>")
        lines.append(
            f"  = {format_rate_value_plain(entry.rate_value)} {entry.target_currency}"
        )
    return lines


class ListMarketRatesScene(BaseTelegramScene, state="market_rates_list"):
    """Scene that shows all available market exchange rates."""

    _TEXT_LINES: ClassVar[list[str]] = ["Рыночные курсы"]

    async def _payload_for_enter(
        self,
        **kwargs: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup for the market rates list."""
        list_market_rates_use_case = cast(
            ListMarketRatesUseCase,
            kwargs["list_market_rates_use_case"],
        )
        result = await list_market_rates_use_case.execute()
        text_lines = _build_market_rates_lines(
            result,
            text_lines=list(self._TEXT_LINES),
        )
        text = "\n".join(text_lines)
        markup = await self._reply_markup()
        return text, markup

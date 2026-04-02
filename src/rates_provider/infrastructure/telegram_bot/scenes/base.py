"""Base scene primitives for Telegram bot conversation flow."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ClassVar

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.scene import Scene, on
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..callbacks.navigation import BackNavigationCallback


def _prepare_scene_data_for_enter(
    data: dict[str, Any],
    *,
    ui_message_id_key: str,
    fresh_ui_message: bool,
) -> dict[str, Any]:
    """Prepare scene data before enter, optionally forcing a fresh UI message."""
    prepared_data = dict(data)
    if fresh_ui_message:
        prepared_data.pop(ui_message_id_key, None)
    return prepared_data


def handle_exceptions(
    error_message_builder: Callable[[Exception], str],
    *handled_errors: type[Exception],
) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
    """Wrap a message handler and render selected exceptions as scene errors."""

    def decorator(handler: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        """Apply exception-to-UI rendering for the provided handler."""

        @wraps(handler)
        async def wrapped(
            self: "BaseTelegramScene",
            message: Message,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            """Execute handler and render mapped errors in the current scene."""
            try:
                await handler(self, message, *args, **kwargs)
            except handled_errors as error:
                text, reply_markup = await self._payload(
                    error_text=error_message_builder(error),
                    user_input=message.text or "",
                )
                await self._render_for_message(message, text, reply_markup)

        return wrapped

    return decorator


class BaseTelegramScene(Scene):
    """Common base class for Telegram scenes with optional back navigation."""

    _TEXT_LINES: ClassVar[list[str]] = []
    _PROMPT_TEXT: ClassVar[str] = ""
    _BUTTONS: ClassVar[list[InlineKeyboardButton]] = []
    _BACK_CALLBACK_DATA: ClassVar[str] = BackNavigationCallback().pack()
    _BACK_BUTTON_TEXT: ClassVar[str] = "⬅️ Назад"
    _UI_MESSAGE_ID_KEY: ClassVar[str] = "ui_message_id"

    async def _has_previous_scene(self) -> bool:
        """Return True when there is a scene in history for rollback."""
        previous_scene = await self.wizard.manager.history.get()
        return previous_scene is not None

    def _configured_rows(self) -> list[list[InlineKeyboardButton]]:
        """Build button rows from class-level declarative button config."""
        return [[button] for button in self._BUTTONS]

    async def _create_base_lines(self) -> list[str]:
        """Create base text lines without error. Override in subclasses for custom logic."""
        if self._PROMPT_TEXT and self._TEXT_LINES:
            return [*self._TEXT_LINES, "", self._PROMPT_TEXT]
        if self._PROMPT_TEXT:
            return [self._PROMPT_TEXT]
        return self._TEXT_LINES

    async def _get_text(
        self,
        error_text: str | None = None,
        user_input: str | None = None,
    ) -> str:
        """Build scene text from lines joined with newlines."""
        lines = await self._create_base_lines()
        if error_text is not None:
            lines = lines + ["", error_text]
            if user_input is not None:
                shown_input = user_input.strip() or "<пусто>"
                lines.append(f"Вы ввели: {shown_input}")
        return "\n".join(lines)

    async def _payload(
        self,
        error_text: str | None = None,
        user_input: str | None = None,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build text and markup payload using _get_text() and buttons."""
        text = await self._get_text(error_text=error_text, user_input=user_input)
        markup = await self._reply_markup()
        return text, markup

    async def _build_markup(
        self,
        rows: list[list[InlineKeyboardButton]],
    ) -> InlineKeyboardMarkup | None:
        """Finalize keyboard rows by appending back navigation when available."""
        if await self._has_previous_scene():
            rows.append(
                [
                    InlineKeyboardButton(
                        text=self._BACK_BUTTON_TEXT,
                        callback_data=self._BACK_CALLBACK_DATA,
                    )
                ]
            )

        if not rows:
            return None
        return InlineKeyboardMarkup(inline_keyboard=rows)

    async def _reply_markup(self) -> InlineKeyboardMarkup | None:
        """Build keyboard with scene buttons and auto-added back button."""
        return await self._build_markup(self._configured_rows())

    async def _payload_for_enter(
        self,
        **_: Any,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """Build scene payload for enter handlers that receive injected dependencies."""
        return await self._payload()

    async def _render_for_message(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> None:
        """Render scene from a message event, reusing UI shell when available."""
        data = await self.wizard.get_data()
        ui_message_id = data.get(self._UI_MESSAGE_ID_KEY)
        bot = message.bot

        if isinstance(ui_message_id, int) and bot is not None:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=ui_message_id,
                    text=text,
                    reply_markup=reply_markup,
                )
                return
            except TelegramBadRequest as error:
                if "message is not modified" in str(error).lower():
                    return
                pass

        ui_message = await message.answer(text, reply_markup=reply_markup)
        await self.wizard.update_data({self._UI_MESSAGE_ID_KEY: ui_message.message_id})


    @on.callback_query(BackNavigationCallback.filter())
    async def on_back_click(
        self,
        callback_query: CallbackQuery,
    ) -> None:
        """Return to the previous scene using scene history."""
        await callback_query.answer()
        if not await self._has_previous_scene():
            return
        await self.wizard.back()

    @on.message.enter()
    async def on_enter_from_message(self, message: Message, **kwargs: Any) -> None:
        """Render scene when entered from a message event."""
        text, reply_markup = await self._payload_for_enter(**kwargs)
        await self._render_for_message(message, text, reply_markup)

    @on.callback_query.enter()
    async def on_enter_from_callback(
        self,
        callback_query: CallbackQuery,
        **kwargs: Any,
    ) -> None:
        """Render scene by editing the current UI message when entered from a callback."""
        await callback_query.answer()
        message = callback_query.message
        if not isinstance(message, Message):
            return
        text, reply_markup = await self._payload_for_enter(**kwargs)
        await message.edit_text(text, reply_markup=reply_markup)
        await self.wizard.update_data({self._UI_MESSAGE_ID_KEY: message.message_id})

    @staticmethod
    async def _best_effort_delete_user_message(message: Message) -> None:
        """Delete user message silently; keep flow alive on Telegram API failure."""
        try:
            await message.delete()
        except TelegramAPIError:
            return

    async def collapse_to(
        self,
        scene_type: type[Scene] | State | str | None,
        fresh_ui_message: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Схлопывает текущую ветку истории до указанной сцены.

        Пример:
            history: [Menu, AddClothes, ShortsSize]
            current: ShortsPrice

            await self.collapse_to(AddClothesScene)

        Результат:
            history: [Menu]
            current: AddClothes
        """
        manager = self.wizard.manager

        # Аналогично ScenesManager.enter(None): полностью выйти из flow
        if scene_type is None:
            await self.wizard.leave(_with_history=False, **kwargs)
            await manager.history.clear()
            await manager.enter(None, _check_active=False, **kwargs)
            return

        # Приводим type[Scene] | State | str к реальному классу сцены,
        # чтобы получить её canonical state
        target_scene_cls = manager.registry.get(scene_type)
        target_state = target_scene_cls.__scene_config__.state

        if target_state is None:
            raise RuntimeError("Target scene has no state")

        # Не добавляем текущую сцену в history
        await self.wizard.leave(_with_history=False, **kwargs)

        # Считываем текущую историю
        records = await manager.history.all()

        # Ищем последнюю запись target_state в истории
        target_index: int | None = None
        for i in range(len(records) - 1, -1, -1):
            if records[i].state == target_state:
                target_index = i
                break

        if target_index is None:
            raise RuntimeError(
                f"Scene {target_state!r} not found in wizard history"
            )

        target_record = records[target_index]
        keep_history = records[:target_index]

        # Пересобираем history: оставляем только предков target-сцены
        await manager.history.clear()
        for rec in keep_history:
            await manager.history.push(rec.state, rec.data)

        # Восстанавливаем data той сцены, к которой схлопываемся
        target_data = _prepare_scene_data_for_enter(
            target_record.data,
            ui_message_id_key=self._UI_MESSAGE_ID_KEY,
            fresh_ui_message=fresh_ui_message,
        )
        await self.wizard.state.set_data(target_data)

        # Делаем target текущей активной сценой
        await manager.enter(scene_type, _check_active=False, **kwargs)

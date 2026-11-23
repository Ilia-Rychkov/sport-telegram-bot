import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent, Message

from backend.services.main_menu import MainMenuService

logger = logging.getLogger(__name__)
router = Router()

# Создаем сервис для получения текста "Не понимаю"
menu_service = MainMenuService()


@router.error()
async def handle_error(event: ErrorEvent, state: FSMContext | None = None):
    logger.error("Ошибка при обработке обновления Telegram", exc_info=event.exception)

    message = event.update.message
    if event.update.callback_query is not None:
        message = event.update.callback_query.message
    if not isinstance(message, Message):
        return

    if state is not None:
        await state.clear()
    try:
        await message.answer(
            "Возникла техническая ошибка. Попробуй позже.",
            reply_markup=menu_service.get_main_keyboard(),
        )
    except TelegramAPIError:
        logger.exception("Не удалось отправить сообщение об ошибке")


@router.message()
async def unknown_message(message: Message):
    """Ловушка для всех нераспознанных сообщений."""
    await message.answer(
        menu_service.get_unknown_text()
    )

from aiogram import Router
from aiogram.types import Message

from backend.services.main_menu import MainMenuService

router = Router()

# Создаем сервис для получения текста "Не понимаю"
menu_service = MainMenuService()


@router.message()
async def unknown_message(message: Message):
    """Ловушка для всех нераспознанных сообщений."""
    await message.answer(
        menu_service.get_unknown_text()
    )
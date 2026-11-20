from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import CallbackQuery

from backend.services.main_menu import MainMenuService
from backend.services.interfaces.main_menu_service import IMainMenuService

from bot.keyboards.main import get_main_menu_keyboard

router = Router()

# Создаем экземпляр сервиса (пока без зависимостей вроде БД)
menu_service: IMainMenuService = MainMenuService()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.delete()  # Удаляем сообщение с кнопкой
    await callback.message.answer(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()  # Закрываем "часики" на кнопке

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    # Хендлер только управляет состоянием и отправляет ответ.
    # Вся текстовая и клавиатурная логика - в сервисе.
    await state.clear()

    await message.answer(
        menu_service.get_welcome_text(),
        reply_markup=menu_service.get_main_keyboard(),
    )


@router.message(F.text == "Помощь")
async def help_message(message: Message):
    await message.answer(menu_service.get_help_text())


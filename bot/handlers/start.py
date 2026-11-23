import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError

from backend.services.main_menu import MainMenuService
from backend.services.interfaces.main_menu_service import IMainMenuService
from backend.services.profile_service import ProfileService

from bot.keyboards.labels import make_button
from bot.keyboards.main import get_main_menu_keyboard
from database.models import DEFAULT_WEIGHT_REMINDER_DAYS
from database.weight import get_last_weight

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляр сервиса (пока без зависимостей вроде БД)
menu_service: IMainMenuService = MainMenuService()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()  # Удаляем сообщение с кнопкой
    await callback.message.answer(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()  # Закрываем "часики" на кнопке

@router.message(CommandStart())
async def start(message: Message, state: FSMContext, profile_service: ProfileService):
    await state.clear()

    if message.from_user is not None:
        telegram_id = message.from_user.id
        try:
            profile = profile_service.get_profile(telegram_id)
            if profile:
                last_weight = await asyncio.to_thread(get_last_weight, telegram_id)
                if last_weight is None:
                    keyboard = menu_service.get_main_keyboard()
                    keyboard.keyboard.append([make_button("Записать вес")])
                    await message.answer(
                        "В истории пока нет измерений. Нажми «Записать вес», чтобы добавить первое.",
                        reply_markup=keyboard,
                    )
                    return

                recorded_at = last_weight.recorded_at
                if recorded_at.tzinfo is None:
                    recorded_at = recorded_at.replace(tzinfo=timezone.utc)

                interval = profile.get("weight_reminder_days", DEFAULT_WEIGHT_REMINDER_DAYS)
                if datetime.now(timezone.utc) - recorded_at >= timedelta(days=interval):
                    await message.answer(
                        "Пора записать вес. Новое измерение можно добавить в разделе «Прогресс».",
                        reply_markup=menu_service.get_main_keyboard(),
                    )
                    return
        except SQLAlchemyError:
            logger.exception("Не удалось проверить последнее измерение веса")

    await message.answer(
        menu_service.get_welcome_text(),
        reply_markup=menu_service.get_main_keyboard(),
    )


@router.message(F.text == "Позже")
async def postpone_weight(message: Message):
    await message.answer(
        "Записать вес можно в разделе «Прогресс».",
        reply_markup=menu_service.get_main_keyboard(),
    )


@router.message(F.text == "Помощь")
async def help_message(message: Message):
    await message.answer(menu_service.get_help_text())


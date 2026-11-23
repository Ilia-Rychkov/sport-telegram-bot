import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation
from dotenv import load_dotenv

from bot.keyboards.labels import normalize_button_input
from bot.middlewares.db import DatabaseMiddleware

from bot.handlers.start import router as start_router
from bot.handlers.profile import router as profile_router
from bot.handlers.nutrition import router as nutrition_router
from bot.handlers.progress import router as progress_router
from bot.handlers.nutrition_allergies import router as nutrition_allergies_router
from bot.handlers.fallback import router as fallback_router

from bot.handlers.workout_menu import router as workout_menu_router
from bot.handlers.workout_record import router as workout_record_router
from bot.handlers.workout_plan import router as workout_plan_router

load_dotenv(Path(__file__).resolve().parent.parent / ".env")




from database.database import create_db_and_tables  # <-- Импорт

async def main():
    logging.basicConfig(level=logging.INFO)
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Добавь BOT_TOKEN в файл .env")

    # Создаём таблицы (если их нет)
    create_db_and_tables()  # <-- ВЫЗОВ

    dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())
    dispatcher.message.outer_middleware(normalize_button_input)
    dispatcher.message.middleware(DatabaseMiddleware())

    # 3. Регистрируем роутеры.
    dispatcher.include_router(start_router)
    dispatcher.include_router(profile_router)
    dispatcher.include_router(nutrition_allergies_router)
    dispatcher.include_router(nutrition_router)
    dispatcher.include_router(progress_router)

    dispatcher.include_router(workout_menu_router)  # <-- Меню тренировок
    dispatcher.include_router(workout_record_router)  # <-- Запись тренировок
    dispatcher.include_router(workout_plan_router)  # <-- План тренировок


    dispatcher.include_router(fallback_router)

    # 4. Запускаем бота
    async with Bot(token=token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

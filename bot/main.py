from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from database.profiles import get_profile
from database.weight import get_last_weight

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import SimpleEventIsolation

from bot.handlers.profile import router as profile_router
from bot.handlers.nutrition import router as nutrition_router
from bot.handlers.workout_record import router as workout_record_router
from bot.handlers.progress import router as progress_router

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    ErrorEvent,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)


router = Router()

from bot.keyboards.main_menu import main_menu

weight_reminder_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Записать вес"),
            KeyboardButton(text="Позже"),
        ],
    ],
    resize_keyboard=True,
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    data = await state.get_data()
    cached_profile = data.get("profile")

    await state.clear()

    if cached_profile is not None:
        await state.update_data(profile=cached_profile)

    try:
        profile = await asyncio.to_thread(
            get_profile,
            message.from_user.id,
        )

        last_weight = None

        if profile is not None:
            last_weight = await asyncio.to_thread(
                get_last_weight,
                message.from_user.id,
            )
    except SQLAlchemyError:
        logging.exception("Не удалось проверить последнее измерение веса")
        await message.answer(
            "Не удалось проверить историю веса. "
            "Выбери раздел в меню:",
            reply_markup=main_menu,
        )
        return

    # Сначала нужна заполненная анкета.
    if profile is None:
        await message.answer(
            "Привет! Начни с раздела «Мой профиль» — "
            "заполни и подтверди анкету.",
            reply_markup=main_menu,
        )
        return

    if last_weight is None:
        await message.answer(
            "В истории пока нет измерений веса. "
            "Хочешь записать первое?",
            reply_markup=weight_reminder_menu,
        )
        return

    recorded_at = last_weight.recorded_at

    # SQLite может вернуть дату без информации о часовом поясе.
    # Наши даты при записи создаются в UTC.
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)

    elapsed = datetime.now(timezone.utc) - recorded_at

    if elapsed >= timedelta(days=2):
        await message.answer(
            "Ты не записывал вес уже два дня или больше. "
            "Хочешь добавить новое измерение?",
            reply_markup=weight_reminder_menu,
        )
        return

    await message.answer(
        "Привет! Выбери раздел в меню:",
        reply_markup=main_menu,
    )


@router.message(F.text == "Помощь")
async def help_message(message: Message):
    await message.answer(
        "Выбери раздел с помощью кнопок внизу.\n"
        "Чтобы снова открыть главное меню, отправь /start."
    )

@router.message(F.text == "Позже")
async def postpone_weight(message: Message):
    await message.answer(
        "Хорошо. Записать вес можно в разделе «Прогресс».\n"
        "Выбери раздел:",
        reply_markup=main_menu,
    )

@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "Не понимаю эту команду или сообщение.\n"
        "/start — главное меню\n"
        "/cancel — отменить заполнение анкеты"
    )


@router.error()
async def handle_error(event: ErrorEvent):
    logging.error(
        "Ошибка при обработке обновления",
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        ),
    )

    message = event.update.message

    if message:
        try:
            await message.answer(
                "Произошла ошибка. Попробуй ещё раз чуть позже."
            )
        except Exception:
            logging.exception("Не удалось отправить сообщение об ошибке")

    return True


async def main():
    logging.basicConfig(level=logging.INFO)

    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("Добавь BOT_TOKEN в файл .env")

    dispatcher = Dispatcher(
    events_isolation=SimpleEventIsolation()
)

    dispatcher.include_router(profile_router)
    dispatcher.include_router(nutrition_router)
    dispatcher.include_router(workout_record_router)
    dispatcher.include_router(progress_router)
    dispatcher.include_router(router)

    async with Bot(token=token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import logging
import os
from pathlib import Path

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import SimpleEventIsolation

from bot.handlers.profile import router as profile_router

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    ErrorEvent,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

router = Router()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Мой профиль"),
            KeyboardButton(text="Питание"),
        ],
        [
            KeyboardButton(text="Тренировки"),
            KeyboardButton(text="Прогресс"),
        ],
        [KeyboardButton(text="Помощь")],
    ],
    resize_keyboard=True,
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile")

    await state.clear()

    if profile is not None:
        await state.update_data(profile=profile)

    await message.answer(
        "Привет! Я помогу следить за питанием, тренировками "
        "и прогрессом.\nВыбери раздел в меню:",
        reply_markup=main_menu,
    )


@router.message(F.text == "Помощь")
async def help_message(message: Message):
    await message.answer(
        "Выбери раздел с помощью кнопок внизу.\n"
        "Чтобы снова открыть главное меню, отправь /start."
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
    dispatcher.include_router(router)

    async with Bot(token=token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
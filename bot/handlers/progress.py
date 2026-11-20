import asyncio
import logging
from math import isfinite

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    Message,
    ReplyKeyboardRemove,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.services.weight_chart import build_weight_chart
from backend.services.workout_db_service import get_workout_history
from bot.keyboards.main_menu import main_menu
from bot.keyboards.progress import (
    PERIOD_OPTIONS,
    period_menu,
    progress_menu,
)
from database.weight import add_weight, get_weight_history


logger = logging.getLogger(__name__)
router = Router()


class ProgressForm(StatesGroup):
    weight = State()
    period = State()


async def clear_input(state: FSMContext):
    # Убираем незавершённый ввод, сохраняя профиль в FSM.
    data = await state.get_data()
    profile = data.get("profile")

    await state.clear()

    if profile is not None:
        await state.update_data(profile=profile)


@router.message(F.text == "Главное меню")
async def return_to_main(message: Message, state: FSMContext):
    await clear_input(state)
    await message.answer(
        "Выбери раздел:",
        reply_markup=main_menu,
    )


@router.message(F.text == "Прогресс")
async def open_progress(message: Message, state: FSMContext):
    await clear_input(state)
    await message.answer(
        "Записывай вес и смотри его изменение на графике.\n"
        "Также здесь доступна история тренировок.",
        reply_markup=progress_menu,
    )


@router.message(F.text == "Записать вес")
async def ask_weight(message: Message, state: FSMContext):
    await clear_input(state)
    await state.set_state(ProgressForm.weight)

    await message.answer(
        "Введи текущий вес в килограммах, например 71,5.\n"
        "Для отмены отправь /cancel или /start.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(
    ProgressForm.weight,
    F.text,
    ~F.text.startswith("/"),
)
async def receive_weight(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    try:
        weight = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например 71 или 71,5.")
        return

    if not isfinite(weight) or not 30 <= weight <= 350:
        await message.answer("Вес должен быть от 30 до 350 кг.")
        return

    try:
        await asyncio.to_thread(
            add_weight,
            message.from_user.id,
            weight,
        )
    except ValueError as error:
        await clear_input(state)
        await message.answer(
            str(error),
            reply_markup=main_menu,
        )
        return
    except SQLAlchemyError:
        logger.exception("Не удалось записать вес")
        await message.answer(
            "Не удалось сохранить вес. Попробуй ввести его ещё раз."
        )
        return

    # Питание читает базу, но обновляем и копию профиля в FSM.
    data = await state.get_data()
    profile = data.get("profile")

    if profile is not None:
        profile = profile.copy()
        profile["weight"] = weight
        profile.pop("norms", None)
        await state.update_data(profile=profile)

    await clear_input(state)
    await message.answer(
        f"Вес {weight:g} кг записан. Выбери раздел:",
        reply_markup=main_menu,
    )


@router.message(F.text == "График веса")
async def choose_period(message: Message, state: FSMContext):
    await clear_input(state)
    await state.set_state(ProgressForm.period)

    await message.answer(
        "За какой период показать изменение веса?",
        reply_markup=period_menu,
    )


@router.message(
    ProgressForm.period,
    F.text.in_(PERIOD_OPTIONS),
)
async def send_weight_chart(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    period_label = message.text
    days = PERIOD_OPTIONS[period_label]

    try:
        entries = await asyncio.to_thread(
            get_weight_history,
            message.from_user.id,
            days,
        )
    except SQLAlchemyError:
        logger.exception("Не удалось загрузить историю веса")
        await message.answer(
            "Не удалось загрузить измерения. Выбери период ещё раз.",
            reply_markup=period_menu,
        )
        return

    if not entries:
        await clear_input(state)
        await message.answer(
            "За этот период измерений нет. "
            "Открой «Прогресс» → «Записать вес».",
            reply_markup=main_menu,
        )
        return

    try:
        chart = await asyncio.to_thread(
            build_weight_chart,
            entries,
            period_label.lower(),
        )
    except Exception:
        logger.exception("Не удалось построить график веса")
        await message.answer(
            "Не удалось построить график. Выбери период ещё раз.",
            reply_markup=period_menu,
        )
        return

    await message.answer_photo(
        photo=BufferedInputFile(
            chart,
            filename="weight_progress.png",
        ),
        caption=(
            f"Изменение веса: {period_label.lower()}.\n"
            f"Измерений: {len(entries)}."
        ),
        reply_markup=main_menu,
    )
    await clear_input(state)


@router.message(F.text == "История тренировок")
async def show_workout_history(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None:
        return

    await clear_input(state)

    try:
        history = await asyncio.to_thread(
            get_workout_history,
            message.from_user.id,
            limit=5,
        )
    except SQLAlchemyError:
        logger.exception("Не удалось загрузить тренировки")
        await message.answer(
            "Не удалось загрузить историю. Попробуй позже.",
            reply_markup=main_menu,
        )
        return

    if not history:
        await message.answer(
            "У тебя пока нет записанных тренировок.\n"
            "Нажми «Тренировки», чтобы записать первую.",
            reply_markup=main_menu,
        )
        return

    await message.answer(
        "Твоя история тренировок — последние 5:",
        reply_markup=main_menu,
    )

    for session in history:
        lines = [f"Дата: {session['date']}"]

        if session["notes"]:
            lines.append(session["notes"])

        for exercise in session["exercises"]:
            weight = (
                f"{exercise['weight']:g} кг"
                if exercise["weight"] > 0
                else "без веса"
            )
            lines.append(
                f"• {exercise['name']}: {weight} × "
                f"{exercise['sets']} подх. × "
                f"{exercise['reps']} повт."
            )

        # Разбиваем длинный текст, чтобы уложиться в лимит Telegram.
        text = "\n".join(lines)
        for start in range(0, len(text), 4000):
            await message.answer(
                text[start:start + 4000],
                parse_mode=None,
            )


@router.message(ProgressForm())
async def unexpected_progress_answer(message: Message):
    if message.text and message.text.startswith("/"):
        # Передаём команды следующим роутерам, включая /start.
        from aiogram.dispatcher.event.bases import SkipHandler

        raise SkipHandler

    await message.answer(
        "Введи вес числом или выбери период кнопкой.\n"
        "Для выхода отправь /start."
    )
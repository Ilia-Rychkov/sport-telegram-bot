import logging
from html import escape
from math import isfinite
from sys import float_info

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.services.interfaces.workout_service import IWorkoutService
from backend.services.interfaces.workout_parser_service import IWorkoutParserService
from bot.handlers.workout_menu import get_workout_menu
from bot.keyboards.main import get_main_menu_keyboard
from bot.keyboards.profile import make_keyboard

logger = logging.getLogger(__name__)
router = Router()
MAX_COUNT = 2**63 - 1


class WorkoutRecordForm(StatesGroup):
    waiting_for_text = State()
    asking_weight = State()
    asking_sets = State()
    asking_reps = State()


@router.message(F.text == "Записать тренировку")
async def start_workout_record(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(WorkoutRecordForm.waiting_for_text)
    await message.answer(
        "🏋️ Расскажи, что сделал на тренировке.\n"
        "Можешь написать всё сразу, например:\n"
        "«Жим лёжа 50 кг, 3 подхода по 10 повторений»",
        reply_markup=make_keyboard(["Отмена"]),
    )


@router.message(WorkoutRecordForm(), Command("cancel"))
@router.message(WorkoutRecordForm(), F.text.in_({"Отмена", "Главное меню"}))
async def cancel_workout_record(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Запись тренировки отменена.", reply_markup=get_main_menu_keyboard())


@router.message(WorkoutRecordForm.waiting_for_text, F.text)
async def process_natural_text(
    message: Message,
    state: FSMContext,
    workout_parser: IWorkoutParserService,
    workout_service: IWorkoutService,
):
    thinking_msg = await message.answer("⏳ Анализирую твой текст...")
    parsed = await workout_parser.parse_workout(message.text)

    if parsed is None:
        await state.clear()
        await thinking_msg.delete()
        await message.answer(
            "Не удалось разобрать тренировку. Попробуй позже.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    if not isinstance(parsed, list) or not parsed or any(
        not isinstance(ex, dict)
        or not isinstance(ex.get("exercise"), str)
        or not ex["exercise"].strip()
        for ex in parsed
    ):
        await thinking_msg.edit_text(
            "🤔 Не совсем понял. Попробуй написать так:\n"
            "«Жим лёжа 50 кг, 3 подхода по 10 повторений»"
        )
        return

    await thinking_msg.delete()

    for exercise in parsed:
        weight = exercise.get("weight")
        exercise["weight"] = (
            float(weight) if type(weight) in (int, float) and 0 <= weight <= float_info.max else None
        )
        for field in ("sets", "reps"):
            count = exercise.get(field)
            exercise[field] = (
                int(count)
                if type(count) in (int, float) and 1 <= count <= MAX_COUNT and int(count) == count
                else None
            )
    await state.update_data(exercises=parsed, exercise_index=0)
    await continue_workout_record(message, state, workout_service)


@router.message(WorkoutRecordForm.asking_weight, F.text)
async def receive_weight(message: Message, state: FSMContext, workout_service: IWorkoutService):
    try:
        weight = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("Введи вес числом, например 50 или 0.")
        return
    if not isfinite(weight) or weight < 0:
        await message.answer("Введи неотрицательный вес, например 50 или 0.")
        return

    data = await state.get_data()
    exercise = data["exercises"][data["exercise_index"]]
    exercise["weight"] = weight
    await state.update_data(exercises=data["exercises"])
    await continue_workout_record(message, state, workout_service)


@router.message(WorkoutRecordForm.asking_sets, F.text)
@router.message(WorkoutRecordForm.asking_reps, F.text)
async def receive_count(message: Message, state: FSMContext, workout_service: IWorkoutService):
    asking_sets = await state.get_state() == WorkoutRecordForm.asking_sets.state
    try:
        count = int(message.text.strip())
        if not 1 <= count <= MAX_COUNT:
            raise ValueError
    except ValueError:
        label = "подходов" if asking_sets else "повторений"
        await message.answer(f"Введи целое положительное число {label}.")
        return

    data = await state.get_data()
    exercises = data["exercises"]
    field = "sets" if asking_sets else "reps"
    exercises[data["exercise_index"]][field] = count
    await state.update_data(exercises=exercises)
    await continue_workout_record(message, state, workout_service)


async def continue_workout_record(message: Message, state: FSMContext, workout_service: IWorkoutService):
    data = await state.get_data()
    exercises = data["exercises"]
    for index in range(data["exercise_index"], len(exercises)):
        exercise = exercises[index]
        if all(exercise[field] is not None for field in ("weight", "sets", "reps")):
            continue

        await state.update_data(exercise_index=index)
        if exercise["weight"] is None:
            await state.set_state(WorkoutRecordForm.asking_weight)
            await message.answer(
                f"{exercise['exercise']}: какой был вес в кг? Если без дополнительного веса, введи 0."
            )
        elif exercise["sets"] is None:
            await state.set_state(WorkoutRecordForm.asking_sets)
            await message.answer(f"{exercise['exercise']}: сколько было подходов?")
        else:
            await state.set_state(WorkoutRecordForm.asking_reps)
            await message.answer(f"{exercise['exercise']}: сколько повторений было в каждом подходе?")
        return

    session_id = workout_service.save_workout_batch(
        telegram_id=message.from_user.id,
        exercises=exercises,
        notes="Запись через бота"
    )

    lines = ["✅ <b>Тренировка сохранена!</b>\n"]
    for ex in exercises:
        weight = f"{ex['weight']:g} кг" if ex["weight"] else "без веса"
        lines.append(
            f"• <b>{escape(ex['exercise'].capitalize())}</b>: {weight}, "
            f"{ex['sets']} подх. × {ex['reps']} повт."
        )
    lines.append(f"\n📝 Сессия #{session_id}")

    await state.clear()
    await message.answer(
        "\n".join(lines),
        reply_markup=get_workout_menu(),  # <-- Возвращаем подменю
        parse_mode="HTML",
    )

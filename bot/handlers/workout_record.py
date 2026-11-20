from bot.keyboards.main_menu import main_menu
import logging
from aiogram import Router, F
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.services.workout_service import WorkoutService
from backend.services.workout_parser_service import WorkoutParserService

logger = logging.getLogger(__name__)
router = Router()

workout_cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]],
    resize_keyboard=True,
)

class WorkoutRecordForm(StatesGroup):
    waiting_for_text = State()
    ask_weight = State()
    ask_sets = State()
    ask_reps = State()


@router.message(F.text == "Тренировки")
async def start_workout_record(message: Message, state: FSMContext):
    await state.set_state(WorkoutRecordForm.waiting_for_text)
    await message.answer(
        "🏋️ Расскажи, что сделал на тренировке.\n"
        "Можешь написать всё сразу, например: «Жим лежа 50 кг на 10 раз, 3 подхода» или «Отжимания 3 по 15».",
        reply_markup=workout_cancel_menu,
    )


@router.message(WorkoutRecordForm(), F.text == "Отмена")
async def cancel_workout_record(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Запись тренировки отменена.", reply_markup=main_menu)


@router.message(WorkoutRecordForm.waiting_for_text, F.text)
async def process_natural_text(
    message: Message,
    state: FSMContext,
    workout_parser: WorkoutParserService,
    workout_service: WorkoutService,
):
    # 1. Отправляем в AI
    thinking_msg = await message.answer("⏳ Анализирую твой текст...")
    parsed = await workout_parser.parse_workout(message.text)

    if not parsed or not parsed.get("exercise"):
        await thinking_msg.edit_text(
            "🤔 Не совсем понял. Попробуй написать название упражнения и данные (например: «Приседания 100 кг 5х5»)."
        )
        return

    await state.update_data(
        exercise_name=parsed["exercise"],
        weight=parsed.get("weight"),
        sets=parsed.get("sets"),
        reps=parsed.get("reps")
    )
    await thinking_msg.delete()

    # 2. Проверяем, чего не хватает
    if parsed.get("weight") is None:
        await message.answer(
            f"Упражнение **{parsed['exercise']}** записал.\n"
            f"Был ли дополнительный вес (в кг)? Если нет — напиши 0.",
            parse_mode="Markdown"
        )
        await state.set_state(WorkoutRecordForm.ask_weight)
    elif parsed.get("sets") is None:
        await message.answer("Сколько было подходов?")
        await state.set_state(WorkoutRecordForm.ask_sets)
    elif parsed.get("reps") is None:
        await message.answer("Сколько повторений в каждом подходе?")
        await state.set_state(WorkoutRecordForm.ask_reps)
    else:
        await finalize_record(message, state, workout_service)


@router.message(WorkoutRecordForm.ask_weight, F.text)
async def process_weight(message: Message, state: FSMContext, workout_service: WorkoutService):
    try:
        weight = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например 50 или 0 если без веса.")
        return
    await state.update_data(weight=weight)
    data = await state.get_data()
    if data.get("sets") is None:
        await message.answer("Сколько было подходов?")
        await state.set_state(WorkoutRecordForm.ask_sets)
    elif data.get("reps") is None:
        await message.answer("Сколько повторений в каждом подходе?")
        await state.set_state(WorkoutRecordForm.ask_reps)
    else:
        await finalize_record(message, state, workout_service)


@router.message(WorkoutRecordForm.ask_sets, F.text)
async def process_sets(message: Message, state: FSMContext, workout_service: WorkoutService):
    try:
        sets = int(message.text)
        if sets <= 0: raise ValueError
    except ValueError:
        await message.answer("Введи целое положительное число.")
        return
    await state.update_data(sets=sets)
    data = await state.get_data()
    if data.get("reps") is None:
        await message.answer("Сколько повторений в каждом подходе?")
        await state.set_state(WorkoutRecordForm.ask_reps)
    else:
        await finalize_record(message, state, workout_service)


@router.message(WorkoutRecordForm.ask_reps, F.text)
async def process_reps(message: Message, state: FSMContext, workout_service: WorkoutService):
    try:
        reps = int(message.text)
        if reps <= 0: raise ValueError
    except ValueError:
        await message.answer("Введи целое положительное число.")
        return
    await state.update_data(reps=reps)
    await finalize_record(message, state, workout_service)


async def finalize_record(message: Message, state: FSMContext, workout_service: WorkoutService):
    data = await state.get_data()
    telegram_id = message.from_user.id

    # Вызываем сервис
    workout_service.save_full_workout(
        telegram_id=telegram_id,
        exercise_name=data['exercise_name'],
        weight=data.get('weight') or 0.0,
        sets=data['sets'],
        reps=data['reps']
    )

    await state.clear()

    weight_text = f"{data['weight']} кг" if data.get('weight') else "без веса"
    await message.answer(
        f"✅ **{data['exercise_name'].capitalize()}** сохранено!\n"
        f"⚖️ Вес: {weight_text}\n"
        f"🔢 Подходы: {data['sets']} | Повторения: {data['reps']}\n\n"
        f"Выбери раздел в главном меню.",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

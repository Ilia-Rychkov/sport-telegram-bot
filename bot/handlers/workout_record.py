import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.services.interfaces.workout_service import IWorkoutService
from backend.services.interfaces.workout_parser_service import IWorkoutParserService
from bot.handlers.workout_menu import get_workout_menu

logger = logging.getLogger(__name__)
router = Router()


class WorkoutRecordForm(StatesGroup):
    waiting_for_text = State()


@router.message(F.text == "Записать тренировку")
async def start_workout_record(message: Message, state: FSMContext):
    await state.set_state(WorkoutRecordForm.waiting_for_text)
    await message.answer(
        "🏋️ Расскажи, что сделал на тренировке.\n"
        "Можешь написать всё сразу, например:\n"
        "«Жим лежа 50 кг 3х10, приседания 80 кг 4х8, отжимания 3х15»",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(WorkoutRecordForm.waiting_for_text, F.text)
async def process_natural_text(
    message: Message,
    state: FSMContext,
    workout_parser: IWorkoutParserService,
    workout_service: IWorkoutService
):
    thinking_msg = await message.answer("⏳ Анализирую твой текст...")
    parsed = await workout_parser.parse_workout(message.text)

    if not parsed:
        await thinking_msg.edit_text(
            "🤔 Не совсем понял. Попробуй написать так:\n"
            "«Жим лежа 50 кг 3х10, приседания 80 кг 4х8»"
        )
        return

    await thinking_msg.delete()

    # Сохраняем всё одной транзакцией
    session_id = workout_service.save_workout_batch(
        telegram_id=message.from_user.id,
        exercises=parsed,
        notes="Запись через бота"
    )

    # Формируем отчёт
    lines = ["✅ **Тренировка сохранена!**\n"]
    for ex in parsed:
        weight = f"{ex.get('weight')} кг" if ex.get("weight") else "без веса"
        lines.append(
            f"• **{ex['exercise'].capitalize()}**: {weight}, "
            f"{ex.get('sets', '?')} подх. × {ex.get('reps', '?')} повт."
        )
    lines.append(f"\n📝 Сессия #{session_id}")

    await state.clear()
    await message.answer(
        "\n".join(lines),
        reply_markup=get_workout_menu(),  # <-- Возвращаем подменю
        parse_mode="Markdown"
    )
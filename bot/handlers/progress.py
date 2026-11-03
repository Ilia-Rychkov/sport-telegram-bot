import logging
from aiogram import Router, F
from aiogram.types import Message
from backend.services.workout_db_service import get_workout_history

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "Прогресс")
async def show_progress(message: Message):
    telegram_id = message.from_user.id

    history = get_workout_history(telegram_id, limit=5)

    if not history:
        await message.answer(
            "📉 У тебя пока нет записанных тренировок.\n"
            "Нажми «Тренировки», чтобы записать первую!"
        )
        return

    text = "📊 **Твоя история тренировок (последние 5):**\n\n"

    for i, session in enumerate(history, 1):
        text += f"📅 **{session['date']}**\n"
        if session['notes']:
            text += f"_{session['notes']}_\n"

        for ex in session['exercises']:
            weight = f"{ex['weight']} кг" if ex['weight'] > 0 else "без веса"
            text += f"• {ex['name']}: {weight} × {ex['sets']} подх. × {ex['reps']} повт.\n"

        text += "\n"

    text += "Чтобы вернуться в меню, отправь /start."

    await message.answer(text, parse_mode="Markdown")
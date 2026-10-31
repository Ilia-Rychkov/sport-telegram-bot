import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from backend.services.ai_service import parse_workout_text
from bot.handlers.profile import ProfileForm

logger = logging.getLogger(__name__)
router = Router()

@router.message(
    F.text,
    ~F.text.startswith("/"),
    ProfileForm()
)
async def handle_free_text(message: Message, state: FSMContext):
    """
    Ловит свободный текст вне анкеты.
    В будущем здесь будет роутинг по интентам (тренировка, питание, вопрос).
    Сейчас пробуем распарсить как тренировку.
    """
    user_text = message.text
    thinking_msg = await message.answer("⏳ Анализирую...")

    # Пытаемся распарсить как тренировку
    parsed_data = await parse_workout_text(user_text)

    if not parsed_data or not parsed_data.get("exercise"):
        # Если не похоже на тренировку, пока просто говорим об этом
        await thinking_msg.edit_text(
            "🤔 Я пока не понял это сообщение.\n\n"
            "Я умею записывать тренировки (например: «Жим лежа 80 кг на 10 раз, 3 подхода»).\n"
            "Функции питания и ответов на вопросы появятся чуть позже!"
        )
        return

    await thinking_msg.edit_text(
        f"✅ **Распознана тренировка!**\n\n"
        f"🏋️ Упражнение: {parsed_data['exercise'].capitalize()}\n"
        f"⚖️ Вес: {parsed_data.get('weight') or 'Свой вес'} кг\n"
        f"🔁 Повторения: {parsed_data.get('reps') or '-'}\n"
        f"🔢 Подходы: {parsed_data.get('sets') or '-'}\n",
        parse_mode="Markdown"
    )
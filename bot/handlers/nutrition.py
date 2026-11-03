import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from backend.services.ai_service import generate_nutrition_plan

logger = logging.getLogger(__name__)
router = Router()


def split_text(text: str, limit: int = 4000) -> list[str]:
    """Разбивает текст на части, стараясь не резать посередине предложения."""
    if len(text) <= limit:
        return [text]

    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break

        # Ищем последнюю точку или перенос строки в пределах лимита
        split_index = text.rfind('\n\n', 0, limit)
        if split_index == -1:
            split_index = text.rfind('. ', 0, limit)
        if split_index == -1:
            split_index = limit  # Если не нашли, режем жестко

        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()

    return parts


@router.message(F.text == "Питание")
async def handle_nutrition(message: Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile")

    if not profile or "norms" not in profile:
        await message.answer(
            "⚠️ Сначала заполни профиль!\n"
            "Мне нужны твои параметры (вес, рост, цель), чтобы рассчитать калории и составить меню."
        )
        return

    norms = profile["norms"]
    thinking_msg = await message.answer("⏳ Составляю для тебя план питания на день. Это займет около 5-10 секунд...")

    try:
        plan = await generate_nutrition_plan(
            target_calories=norms["calories"],
            target_protein=norms["protein"],
            target_fat=norms["fat"],
            target_carbs=norms["carbs"],
            allergies=[]
        )

        if plan:
            await thinking_msg.delete()

            # Разбиваем текст на безопасные части
            parts = split_text(plan)
            for part in parts:
                try:
                    # Отправляем с HTML-разметкой
                    await message.answer(part, parse_mode="HTML")
                except Exception as e:
                    # Если ИИ ошибся в HTML-тегах (например, незакрытый тег),
                    # отправляем как обычный текст, чтобы сообщение не потерялось
                    logger.warning(f"Ошибка парсинга HTML: {e}. Отправляем как текст.")
                    await message.answer(part)
        else:
            await thinking_msg.edit_text(
                "😔 Извини, не удалось составить план питания. Попробуй позже."
            )

    except Exception as e:
        logger.error(f"Ошибка при генерации питания: {e}")
        # Если сообщение "Думаю..." уже удалено, просто отправляем новое
        try:
            await thinking_msg.edit_text("❌ Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже.")
        except Exception:
            await message.answer("❌ Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже.")
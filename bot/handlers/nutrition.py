from bot.keyboards.main_menu import main_menu

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.exc import SQLAlchemyError

from backend.services.ai_service import generate_nutrition_plan
from backend.services.profile_service import recalculate_profile_norms
from database.profiles import get_profile


logger = logging.getLogger(__name__)
router = Router()


def split_text(text: str, limit: int = 4000) -> list[str]:
    """Разбивает текст на части для отправки в Telegram."""
    parts = []
    text = text.strip()

    while text:
        if len(text) <= limit:
            parts.append(text)
            break

        split_index = text.rfind("\n\n", 0, limit)

        if split_index <= 0:
            split_index = text.rfind(". ", 0, limit)
            if split_index > 0:
                split_index += 1

        if split_index <= 0:
            split_index = limit

        part = text[:split_index].strip()
        if part:
            parts.append(part)

        text = text[split_index:].strip()

    return parts


@router.message(F.text == "Питание")
async def handle_nutrition(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    try:
        saved_profile = await asyncio.to_thread(
            get_profile,
            message.from_user.id,
        )
    except SQLAlchemyError:
        logger.exception("Не удалось загрузить профиль для питания")
        await message.answer(
            "Не удалось загрузить профиль. Попробуй позже."
        )
        return

    if saved_profile is None:
        await message.answer(
            "Сначала заполни и подтверди «Мой профиль»."
        )
        return

    profile = saved_profile.model_dump(
        mode="json",
        include={
            "age", "sex", "height", "weight",
            "activity", "goal", "fitness",
        },
    )

    norms = recalculate_profile_norms(profile)

    if norms is None:
        await message.answer(
            "Не удалось рассчитать нормы. "
            "Проверь параметры в разделе «Мой профиль»."
        )
        return

    profile["norms"] = norms
    await state.update_data(profile=profile)

    thinking_msg = await message.answer(
        "⏳ Составляю для тебя план питания на день..."
    )

    try:
        plan = await generate_nutrition_plan(
            target_calories=norms["calories"],
            target_protein=norms["protein"],
            target_fat=norms["fat"],
            target_carbs=norms["carbs"],
            allergies=[],
        )
    except Exception:
        logger.exception("Ошибка при генерации питания")
        await thinking_msg.edit_text(
            "Не удалось обратиться к ИИ. Попробуй позже."
        )
        return

    if not plan or not plan.strip():
        await thinking_msg.edit_text(
            "Не удалось составить план питания. Попробуй позже."
        )
        return

    for part in split_text(plan):
        try:
            await message.answer(part, parse_mode="HTML")
        except TelegramBadRequest:
            logger.warning(
                "Не удалось отправить часть плана с HTML-разметкой"
            )
            await message.answer(part, parse_mode=None)

    await thinking_msg.delete()
    await message.answer(
        "План питания готов. Выбери раздел в меню.",
        reply_markup=main_menu,
    )
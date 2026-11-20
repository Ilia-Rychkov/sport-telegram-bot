import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.main import get_main_menu_keyboard

from backend.services.profile_service import ProfileService
from backend.services.nutrition_service import NutritionService

logger = logging.getLogger(__name__)
router = Router()


def split_text(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_index = text.rfind('\n\n', 0, limit)
        if split_index == -1:
            split_index = text.rfind('. ', 0, limit)
        if split_index == -1:
            split_index = limit
        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()
    return parts


async def generate_and_send_plan(
    message: Message,
    state: FSMContext,
    profile_service: ProfileService,
    nutrition_service: NutritionService
):
    """Основная логика генерации меню. Вызывается из хендлера и из аллергий."""
    telegram_id = message.from_user.id

    # 1. Идем в БД за профилем
    profile = profile_service.get_profile(telegram_id)

    # 2. Если профиля нет — запускаем анкету
    if not profile:
        from bot.handlers.profile import ask_field
        await state.update_data(came_from_nutrition=True, draft={}, editing_field=None)
        await message.answer("🍏 Чтобы составить меню, мне нужны твои параметры...")
        await ask_field(message, state, "age")
        return

    # 3. Считаем нормы
    norms = profile_service.recalculate_norms(profile)
    if not norms:
        await message.answer("😔 Не удалось рассчитать нормы. Попробуй обновить профиль.")
        return

    # 4. Проверяем аллергии
    allergies_str = profile.get("allergies")

    if allergies_str is None:
        from bot.handlers.nutrition_allergies import ask_for_allergies
        # Сохраняем профиль в FSM, чтобы не потерять при переходе в другой хендлер
        await state.update_data(profile=profile, norms=norms)
        await ask_for_allergies(message, state)
        return

    # 5. Готовим список аллергий
    allergies_list = []
    if allergies_str and allergies_str != "Нет":
        allergies_list = [a.strip() for a in allergies_str.split(",") if a.strip()]

    # 6. Удаляем старое сообщение "думаю..."
    data = await state.get_data()
    old_msg_id = data.get("thinking_msg_id")
    if old_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=old_msg_id)
        except Exception:
            pass

    thinking_msg = await message.answer("⏳ Составляю для тебя план питания...")
    await state.update_data(thinking_msg_id=thinking_msg.message_id)

    # 7. Генерируем план
    plan = await nutrition_service.generate_plan(
        target_calories=norms["calories"],
        target_protein=norms["protein"],
        target_fat=norms["fat"],
        target_carbs=norms["carbs"],
        allergies=allergies_list,
        daily_budget=profile.get("daily_budget")
    )

    await thinking_msg.delete()
    await state.update_data(thinking_msg_id=None)

    if plan:
        for part in split_text(plan):
            try:
                await message.answer(part, parse_mode="HTML")
            except Exception:
                await message.answer(part)

        # Возвращаем клавиатуру главного меню
        await message.answer(
            "Что делаем дальше?",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "😔 Извини, не удалось составить план питания. Попробуй позже.",
            reply_markup=get_main_menu_keyboard()
        )


@router.message(F.text == "Питание")
async def handle_nutrition(
    message: Message,
    state: FSMContext,
    profile_service: ProfileService,
    nutrition_service: NutritionService
):
    """Хендлер кнопки 'Питание'. Просто вызывает основную логику."""
    await generate_and_send_plan(message, state, profile_service, nutrition_service)
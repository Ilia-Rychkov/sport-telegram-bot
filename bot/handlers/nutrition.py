import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from backend.services.ai_service import generate_nutrition_plan

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "Питание")
async def handle_nutrition(message: Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile")

    # 1. Проверяем, заполнен ли профиль
    if not profile or "norms" not in profile:
        await message.answer(
            "⚠️ Сначала заполни профиль!\n"
            "Мне нужны твои параметры (вес, рост, цель), чтобы рассчитать калории и составить меню."
        )
        return

    # 2. Достаем рассчитанные нормы
    norms = profile["norms"]

    # 3. Отправляем сообщение, что бот "думает"
    thinking_msg = await message.answer("⏳ Составляю для тебя план питания на день. Это займет около 5-10 секунд...")

    try:
        # 4. Вызываем нашу функцию из ai_service
        # Обрати внимание: мы передаем именно те цифры, которые посчитал калькулятор
        plan = await generate_nutrition_plan(
            target_calories=norms["calories"],
            target_protein=norms["protein"],
            target_fat=norms["fat"],
            target_carbs=norms["carbs"],
            allergies=[]  # Пока пустой список, потом можно добавить в профиль
        )

        # 5. Обрабатываем результат
        if plan:
            await thinking_msg.edit_text(plan)
        else:
            await thinking_msg.edit_text(
                "😔 Извини, не удалось составить план питания. Попробуй позже."
            )

    except Exception as e:
        logger.error(f"Ошибка при генерации питания: {e}")
        await thinking_msg.edit_text(
            "❌ Произошла ошибка при обращении к ИИ. Попробуй еще раз чуть позже."
        )
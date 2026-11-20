import logging
import random
from backend.services.interfaces.ai_provider import IAIProvider

logger = logging.getLogger(__name__)

import random


class NutritionService:
    def __init__(self, ai_provider: IAIProvider):
        self.ai = ai_provider

    async def generate_plan(self, target_calories, target_protein, target_fat, target_carbs, allergies=None):
        cuisines = ["итальянская", "азиатская", "средиземноморская", "русская", "мексиканская", "французская"]
        cooking_styles = ["быстрые рецепты (до 20 минут)", "блюда в духовке", "салаты и легкие закуски", "супы и рагу",
                          "блюда на сковороде"]

        random_cuisine = random.choice(cuisines)
        random_style = random.choice(cooking_styles)

        allergy_text = f"Исключи ОБЯЗАТЕЛЬНО следующие продукты (аллергии): {', '.join(allergies)}." if allergies else ""

        prompt = f"""
        Ты — профессиональный диетолог. Твоя задача — составить план питания.

        🚨 КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО БЕЗОПАСНОСТИ:
        Если запрошенная калорийность (target_calories) МЕНЬШЕ 1200 ккал, ты ОБЯЗАН немедленно отказаться.
        Твой ответ должен начинаться строго с фразы: "ОТКАЗ: Указанная калорийность опасна для здоровья."

        Параметры пользователя:
        - Калорийность: {target_calories} ккал
        - Белки: {target_protein} г
        - Жиры: {target_fat} г
        - Углеводы: {target_carbs} г
        {allergy_text}

        🎲 РАЗНООБРАЗИЕ:
        Сегодня составь меню в стиле **{random_cuisine} кухни**.
        Предпочтение: **{random_style}**.
        Постарайся использовать разные источники белка (мясо, рыба, яйца, бобовые) и не повторять ингредиенты.

        Составь план из 4-5 приемов пищи.
        Для каждого приема пищи напиши:
        1. Название блюда.
        2. Примерные калории и БЖУ.
        3. Короткий рецепт (2-3 предложения).

        ВАЖНО: Форматируй ответ с помощью HTML-тегов, так как он будет отправлен в Telegram.
        Используй <b>жирный шрифт</b> для заголовков (например, <b>Завтрак</b>) и названий блюд.
        Используй <i>курсив</i> для пояснений.
        НЕ ИСПОЛЬЗУЙ Markdown (никаких #, *, _). Только HTML теги: <b>, <i>, <u>, <s>.
        Используй эмодзи для красоты.
        В конце добавь блок <b>💡 Совет дня</b>, где напиши 1-2 предложения с полезным лайфхаком 
        по питанию или мотивацией, связанной с целью пользователя.
        """

        response_text = await self.ai.generate_text(prompt, temperature=0.8, max_tokens=1500)

        if not response_text:
            return None

        # Проверка безопасности на уровне кода
        if target_calories < 1200:
            if "ОТКАЗ" not in response_text:
                logger.warning("ИИ проигнорировал правило безопасности! Блокируем ответ.")
                return "⚠️ Извините, но указанная калорийность (менее 1200 ккал) опасна для здоровья. Бот не может составить такой рацион."

        return response_text
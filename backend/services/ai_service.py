import os
import logging
import json
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
AI_API_KEY = os.getenv("AI_API_KEY")

WORKER_URL = "https://geminishka.weity-deadliner.workers.dev"

# Модели
MODEL_FAST = "gemini-3.5-flash-lite" # Для парсинга
MODEL_SMART = "gemini-3.5-flash-lite"  # Для генерации

# Инициализация клиента через Воркер
if AI_API_KEY:
    try:
        client = genai.Client(
            api_key=AI_API_KEY,
            http_options=types.HttpOptions(base_url=WORKER_URL)
        )
        logger.info(f"AI клиент инициализирован через воркер: {WORKER_URL}")
    except Exception as e:
        logger.error(f"Ошибка инициализации клиента: {e}")
        client = None
else:
    client = None
    logger.error("AI_API_KEY не найден в переменных окружения!")


# --- 1. ФУНКЦИЯ ПАРСИНГА ---
async def parse_workout_text(user_text: str) -> dict | None:
    """
    Извлекает структурированные данные из естественного текста пользователя.
    """
    if not client:
        return None

    prompt = f"""
    Ты — спортивный ассистент-парсер. Извлеки данные о тренировке из текста пользователя.
    Верни ответ СТРОГО в формате JSON без markdown-разметки (без ```json).

    Формат JSON:
    {{
        "exercise": "название упражнения (строка)",
        "weight": число (кг) или null,
        "reps": число (количество повторений) или null,
        "sets": число (количество подходов) или null
    }}

    Текст пользователя: "{user_text}"
    """

    try:
        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json"
        )

        print(f"[AI] Отправка запроса на парсинг через воркер...")

        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=MODEL_FAST,
                contents=prompt,
                config=config
            ),
            timeout=10.0
        )

        clean_text = response.text.strip()
        # На всякий случай чистим от возможных markdown-тегов, если модель проигнорировала инструкцию
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        result_json = json.loads(clean_text.strip())
        return result_json

    except asyncio.TimeoutError:
        logger.error("Таймаут при запросе к Gemini API (парсинг)")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Gemini вернул невалидный JSON: {e}. Ответ был: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при обращении к Gemini (парсинг): {e}")
        return None


# --- 2. ФУНКЦИЯ ГЕНЕРАЦИИ ПИТАНИЯ ---
async def generate_nutrition_plan(
        target_calories: int,
        target_protein: int,
        target_fat: int,
        target_carbs: int,
        allergies: list[str] = None
) -> str | None:
    """
    Генерирует план питания на основе готовых цифр КБЖУ.
    """
    if not client:
        return None

    allergy_text = f"Исключи следующие продукты (аллергии): {', '.join(allergies)}." if allergies else ""

    prompt = f"""
    Ты — профессиональный диетолог. Твоя задача — составить план питания на один день.

    ВАЖНО: Твои рекомендации не заменяют консультацию врача.

    Параметры пользователя (рассчитаны алгоритмом, не меняй их):
    - Калорийность: {target_calories} ккал
    - Белки: {target_protein} г
    - Жиры: {target_fat} г
    - Углеводы: {target_carbs} г
    {allergy_text}

    Составь план из 4-5 приемов пищи (завтрак, обед, ужин, перекусы). 
    Для каждого приема пищи напиши:
    1. Название блюда.
    2. Примерные калории и БЖУ.
    3. Короткий рецепт (2-3 предложения).

    Ответ должен быть структурированным, красивым и легко читаемым в Telegram. Используй эмодзи.
    """

    try:
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=800
        )

        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=MODEL_SMART,
                contents=prompt,
                config=config
            ),
            timeout=30.0
        )
        return response.text

    except asyncio.TimeoutError:
        logger.error("Таймаут при запросе к Gemini API (генерация питания)")
        return None
    except Exception as e:
        logger.error(f"Ошибка при обращении к Gemini (генерация питания): {e}")
        return None


# --- БЛОК ДЛЯ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ ---
if __name__ == "__main__":
    async def test():
        print("--- Тест 1: Парсинг тренировки ---")
        test_text = "Сделал становую тягу 120 кг на 6 повторений, 4 подхода"
        print(f"Вход: {test_text}")
        result = await parse_workout_text(test_text)
        print("Результат парсинга:", result)

        print("\n[Пауза 3 секунды перед следующим запросом...]")
        await asyncio.sleep(3)

        print("\n--- Тест 2: Генерация питания ---")
        plan = await generate_nutrition_plan(
            target_calories=2000,
            target_protein=150,
            target_fat=60,
            target_carbs=200,
            allergies=["орехи", "лактоза"]
        )
        if plan:
            print("Результат генерации:\n", plan[:300] + "...\n(текст обрезан для вывода)")
        else:
            print("Результат генерации: None (ошибка)")


    asyncio.run(test())
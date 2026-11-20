import logging
import json
from backend.services.interfaces.ai_provider import IAIProvider

logger = logging.getLogger(__name__)


class WorkoutParserService:
    def __init__(self, ai_provider: IAIProvider):
        self.ai = ai_provider

    async def parse_workout(self, user_text: str) -> dict | None:
        prompt = f"""
        Ты — спортивный ассистент-парсер. Извлеки данные о тренировке из текста пользователя.
        Верни ответ СТРОГО в формате JSON без markdown-разметки.

        ВАЖНЫЕ ПРАВИЛА:
        1. Сленг: "100х5 4п" означает вес 100 кг, 5 повторений, 4 подхода.
        2. Если упражнение с собственным весом (отжимания, подтягивания), weight = null.
        3. Если в тексте НЕТ конкретного упражнения (например, "потягал железо", "было тяжко", "привет"), 
           верни СТРОГО {{"exercise": null}}.

        Формат JSON:
        {{
            "exercise": "название упражнения или null",
            "weight": число или null,
            "reps": число или null,
            "sets": число или null
        }}

        Текст пользователя: "{user_text}"
        """

        response_text = await self.ai.generate_text(
            prompt,
            temperature=0.0,
            response_mime_type="application/json"
        )

        if not response_text:
            return None

        # Чистим от возможных markdown-тегов
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            return json.loads(clean_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Gemini вернул невалидный JSON: {e}. Ответ был: {response_text}")
            return None
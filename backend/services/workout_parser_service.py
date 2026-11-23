import logging
import json
from backend.services.interfaces.ai_provider import IAIProvider
from backend.services.interfaces.workout_parser_service import IWorkoutParserService

logger = logging.getLogger(__name__)


class WorkoutParserService(IWorkoutParserService):
    def __init__(self, ai_provider: IAIProvider):
        self.ai = ai_provider

    async def parse_workout(self, user_text: str) -> list[dict] | None:
        prompt = f"""
        Ты — спортивный ассистент-парсер. Извлеки ВСЕ упражнения из текста пользователя.
        Верни ответ СТРОГО в формате JSON-массива без markdown-разметки.

        ВАЖНЫЕ ПРАВИЛА:
        1. Сленг: "100х5 4п" означает вес 100 кг, 5 повторений, 4 подхода.
        2. Если пользователь явно написал «без веса», «с собственным весом» или «0 кг», верни weight = 0.
           Если вес, число подходов или повторений не указаны, верни null в соответствующем поле. Не угадывай значения.
        3. Если в тексте НЕТ конкретных упражнений (например, "потягал железо", "привет"),
           верни СТРОГО пустой массив [].
        4. Изменяй названия на общепринятые или исправляй, если написано с ошибками.

        Формат JSON (массив объектов):
        [
            {{
                "exercise": "название упражнения",
                "weight": число или null,
                "reps": число или null,
                "sets": число или null
            }},
            ...
        ]

        Текст пользователя: "{user_text}"
        """

        response_text = await self.ai.generate_text(
            prompt,
            temperature=0.0,
            response_mime_type="application/json"
        )

        if not response_text:
            return None

        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            data = json.loads(clean_text.strip())
            if isinstance(data, dict):
                if data.get("exercise"):
                    return [data]
                return []
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Gemini вернул невалидный JSON: {e}. Ответ был: {response_text}")
            return None

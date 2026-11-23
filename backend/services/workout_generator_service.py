import logging
from typing import Optional, List, Dict
from backend.services.interfaces.workout_generator_service import IWorkoutGeneratorService
from backend.services.interfaces.ai_provider import IAIProvider

logger = logging.getLogger(__name__)


class WorkoutGeneratorService(IWorkoutGeneratorService):
    def __init__(self, ai_provider: IAIProvider):
        self.ai = ai_provider

    async def generate_plan(
            self,
            profile: Dict,
            location: str,
            equipment: List[str] | None,
            muscle_group: str,
            history: List[Dict]
    ) -> Optional[str]:

        history_text = ""
        if history:
            history_text = "Последние тренировки (учитывай забитость мышц и прогресс):\n"
            for session in history:
                exercises = ", ".join([e["name"] for e in session.get("exercises", [])])
                history_text += f"- {session['date']}: {exercises}\n"

        if equipment is None:
            equipment_text = (
                "Инвентарь не уточняли. Подбирай упражнения с учётом места тренировки "
                "и предлагай замену, если нужного оборудования нет."
            )
        elif equipment:
            equipment_text = f"Доступный инвентарь: {', '.join(equipment)}."
        else:
            equipment_text = "Инвентаря нет, используй только собственный вес."

        prompt = f"""
        Ты — профессиональный персональный тренер. Составь план тренировки.

        Профиль пользователя:
        - Пол: {profile['sex']}
        - Возраст: {profile['age']} лет
        - Вес: {profile['weight']} кг
        - Рост: {profile['height']} см
        - Цель: {profile['goal']}
        - Уровень подготовки: {profile['fitness']}

        Место тренировки: {location}.
        {equipment_text}
        Группа мышц: {muscle_group}.

        {history_text}

        Составь план из 5-7 упражнений с подходами и повторениями.
        Если упражнение с весом — укажи рекомендуемый вес.
        Форматируй ответ с помощью HTML-тегов (<b>, <i>), так как он будет отправлен в Telegram.
        НЕ ИСПОЛЬЗУЙ Markdown (никаких #, *, _).
        ПИШИ КРАТКО И ПО ДЕЛУ.
        """

        return await self.ai.generate_text(prompt, temperature=0.7, max_tokens=2500)

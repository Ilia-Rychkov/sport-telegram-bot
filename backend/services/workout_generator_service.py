import json
import logging
from typing import List, Dict
from backend.services.interfaces.workout_generator_service import IWorkoutGeneratorService, PlannedExercise
from backend.services.interfaces.ai_provider import IAIProvider

logger = logging.getLogger(__name__)

ASSESSMENT_LABELS = {
    "pull_ups": "Подтягивания за один подход",
    "push_ups": "Отжимания за один подход",
    "run_1km": "Время на 1 км (мин:сек)",
}


def format_exercise_result(exercise: Dict) -> str:
    details = []
    weight = exercise.get("weight")
    if weight is not None:
        details.append(f"{weight:g} кг" if weight else "без дополнительного веса")
    if exercise.get("sets") is not None and exercise.get("reps") is not None:
        details.append(f"{exercise['sets']} подх. × {exercise['reps']} повт.")
    return f"{exercise['name']} ({', '.join(details)})" if details else exercise["name"]


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
    ) -> list[PlannedExercise] | None:

        history_text = ""
        if history:
            history_text = "Последние тренировки (учитывай забитость мышц и прогресс):\n"
            for session in history:
                exercises = [format_exercise_result(e) for e in session.get("exercises", [])]
                exercises.extend(
                    f"{entry['name']} (предложено: {entry['instructions']}; оценка: {entry['rating']})"
                    for entry in session.get("feedback", [])
                )
                history_text += f"- {session['date']}: {', '.join(exercises)}\n"

        assessment = profile.get("training_assessment") or {}
        assessment_lines = [
            f"- {label}: {assessment[key]}"
            for key, label in ASSESSMENT_LABELS.items()
            if assessment.get(key) is not None
        ]
        for name, result in profile.get("gym_working_sets", {}).items():
            assessment_lines.append(f"- {name}: {result['weight']:g} кг × {result['reps']} повт.")
        assessment_text = ""
        if assessment_lines:
            assessment_text = "Известные показатели подготовки:\n" + "\n".join(assessment_lines)

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

        {assessment_text}

        Место тренировки: {location}.
        {equipment_text}
        Группа мышц: {muscle_group}.

        {history_text}

        Дай упражнения по порядку, чтобы бот показывал их по одному.
        Учти оценки прошлой нагрузки при подборе упражнений и объёма.
        Верни только JSON-массив из 5–7 объектов с ключами "name" и "instructions".
        В "name" укажи название одного упражнения. В "instructions" кратко напиши, как его делать,
        сколько подходов и повторений, какой отдых и какой вес, если он нужен.
        Используй обычный текст без HTML и Markdown.
        """

        response = await self.ai.generate_text(
            prompt, temperature=0.7, max_tokens=2500, response_mime_type="application/json",
        )
        if not response:
            return None

        try:
            exercises = json.loads(response.strip().removeprefix("```json").removesuffix("```"))
        except json.JSONDecodeError:
            logger.warning("Генератор вернул некорректный JSON плана тренировки")
            return None

        if not isinstance(exercises, list) or not 1 <= len(exercises) <= 7:
            return None

        plan: list[PlannedExercise] = []
        for exercise in exercises:
            if not isinstance(exercise, dict):
                return None
            name = exercise.get("name")
            instructions = exercise.get("instructions")
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
                return None
            if not isinstance(instructions, str) or not 1 <= len(instructions.strip()) <= 900:
                return None
            plan.append({"name": name.strip(), "instructions": instructions.strip()})
        return plan

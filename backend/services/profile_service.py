import logging
from typing import Dict, Any
from backend.services.calculator import calculate_nutrition

logger = logging.getLogger(__name__)

# Словари для перевода текстов из кнопок в английские ключи калькулятора
SEX_MAP = {
    "Мужской": "male",
    "Женский": "female"
}

ACTIVITY_MAP = {
    "Минимальная — преимущественно сидячий день": "low",
    "Низкая — лёгкая активность 1–3 раза в неделю": "light",
    "Средняя — активность 3–5 раз в неделю": "moderate",
    "Высокая — активность 6–7 раз в неделю": "high",
    "Очень высокая — тяжёлая работа или интенсивные нагрузки": "very_high"
}

GOAL_MAP = {
    "Снижение веса": "lose",
    "Набор мышечной массы": "gain",
    "Поддержание веса": "maintain"
}


def recalculate_profile_norms(profile: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Принимает словарь с данными профиля из FSM.
    Возвращает рассчитанные нормы или None в случае ошибки.
    """
    try:
        # Извлекаем и переводим данные
        sex_ru = profile.get("sex")
        activity_ru = profile.get("activity")
        goal_ru = profile.get("goal")

        sex = SEX_MAP.get(sex_ru)
        activity = ACTIVITY_MAP.get(activity_ru)
        goal = GOAL_MAP.get(goal_ru)

        if not all([sex, activity, goal]):
            logger.error(
                f"Не удалось распознать параметры профиля: sex={sex_ru}, activity={activity_ru}, goal={goal_ru}")
            return None

        # Вызываем наш математический калькулятор
        norms = calculate_nutrition(
            sex=sex,
            age=int(profile["age"]),
            height=float(profile["height"]),
            weight=float(profile["weight"]),
            activity=activity,
            goal=goal
        )

        return norms

    except Exception as e:
        logger.error(f"Ошибка при пересчете норм профиля: {e}")
        return None
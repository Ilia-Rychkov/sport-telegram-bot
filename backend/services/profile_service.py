import logging
from typing import Dict, Any, Optional

from sqlmodel import Session, select
from database.models import Profile as DBProfile, User
from backend.services.calculator import calculate_nutrition

logger = logging.getLogger(__name__)

# Словари для перевода
SEX_MAP = {"Мужской": "male", "Женский": "female"}
ACTIVITY_MAP = {
    "Минимальная — преимущественно сидячий день": "low",
    "Низкая — лёгкая активность 1–3 раза в неделю": "light",
    "Средняя — активность 3–5 раз в неделю": "moderate",
    "Высокая — активность 6–7 раз в неделю": "high",
    "Очень высокая — тяжёлая работа или интенсивные нагрузки": "very_high"
}
GOAL_MAP = {"Снижение веса": "lose", "Набор мышечной массы": "gain", "Поддержание веса": "maintain"}


class ProfileService:
    """Сервис для работы с профилем. Принимает сессию БД через конструктор."""

    def __init__(self, session: Session):
        self.session = session

    def get_profile(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        user = self.session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            return None

        db_profile = self.session.exec(select(DBProfile).where(DBProfile.user_id == user.id)).first()

        # Если профиля нет вообще, возвращаем пустой словарь
        if not db_profile:
            return {}

        return {
            "sex": db_profile.sex.value if db_profile.sex else None,
            "age": db_profile.age,
            "weight": db_profile.weight,
            "height": db_profile.height,
            "activity": db_profile.activity.value if db_profile.activity else None,
            "goal": db_profile.goal.value if db_profile.goal else None,
            "fitness": db_profile.fitness.value if db_profile.fitness else None,
            "allergies": db_profile.allergies or None
        }

    def save_profile(self, telegram_id: int, profile_data: Dict[str, Any]) -> None:
        user = self.session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

        db_profile = self.session.exec(select(DBProfile).where(DBProfile.user_id == user.id)).first()
        if not db_profile:
            db_profile = DBProfile(user_id=user.id)
            self.session.add(db_profile)

        # Обновляем ТОЛЬКО те поля, которые не None
        if profile_data.get("sex") is not None:
            db_profile.sex = profile_data["sex"]
        if profile_data.get("age") is not None:
            db_profile.age = int(profile_data["age"])
        if profile_data.get("weight") is not None:
            db_profile.weight = float(profile_data["weight"])
        if profile_data.get("height") is not None:
            db_profile.height = float(profile_data["height"])
        if profile_data.get("activity") is not None:
            db_profile.activity = profile_data["activity"]
        if profile_data.get("goal") is not None:
            db_profile.goal = profile_data["goal"]
        if profile_data.get("fitness") is not None:
            db_profile.fitness = profile_data["fitness"]
        if profile_data.get("allergies") is not None:
            db_profile.allergies = profile_data["allergies"]

        self.session.add(db_profile)
        self.session.commit()

    def recalculate_norms(self, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Если каких-то ключевых данных нет — нормы посчитать нельзя
        required = ["sex", "age", "height", "weight", "activity", "goal"]
        if not all(profile_data.get(k) for k in required):
            return None

        try:
            sex = SEX_MAP.get(profile_data["sex"])
            activity = ACTIVITY_MAP.get(profile_data["activity"])
            goal = GOAL_MAP.get(profile_data["goal"])

            if not all([sex, activity, goal]):
                logger.error(f"Не удалось распознать параметры: {profile_data}")
                return None

            return calculate_nutrition(
                sex=sex,
                age=int(profile_data["age"]),
                height=float(profile_data["height"]),
                weight=float(profile_data["weight"]),
                activity=activity,
                goal=goal
            )
        except Exception as e:
            logger.error(f"Ошибка при пересчете норм: {e}")
            return None
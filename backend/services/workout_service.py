import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from database.models import User, WorkoutSession, ExerciseResult, Exercise

logger = logging.getLogger(__name__)

class WorkoutService:
    def __init__(self, session: Session):
        self.session = session

    def _get_or_create_user(self, telegram_id: int) -> User:
        user = self.session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
        return user

    def create_session(self, telegram_id: int, notes: str = "", workout_id: int | None = None) -> int:
        user = self._get_or_create_user(telegram_id)
        new_session = WorkoutSession(
            user_id=user.id,
            workout_id=workout_id,
            notes=notes
        )
        self.session.add(new_session)
        self.session.commit()
        self.session.refresh(new_session)
        return new_session.id

    def add_result(self, session_id: int, exercise_name: str, weight_kg: float, sets: int, reps: int) -> bool:
        # 1. Ищем или создаем упражнение
        exercise = self.session.exec(select(Exercise).where(Exercise.name == exercise_name)).first()
        if not exercise:
            exercise = Exercise(name=exercise_name, muscle_group="Не указано", technique="Описание появится позже")
            self.session.add(exercise)
            self.session.commit()
            self.session.refresh(exercise)

        # 2. Сохраняем результат
        result = ExerciseResult(
            session_id=session_id,
            exercise_id=exercise.id,
            weight_kg=weight_kg,
            sets=sets,
            reps=reps
        )
        self.session.add(result)
        self.session.commit()
        return True

    def save_full_workout(self, telegram_id: int, exercise_name: str, weight: float, sets: int, reps: int) -> None:
        """Удобный метод: сохраняет сессию и результат одной транзакцией."""
        session_id = self.create_session(telegram_id, notes="Запись через бота")
        self.add_result(session_id, exercise_name, weight, sets, reps)

    def get_history(self, telegram_id: int, limit: int = 5) -> list[dict]:
        user = self.session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            return []

        sessions = self.session.exec(
            select(WorkoutSession).where(WorkoutSession.user_id == user.id)
            .order_by(WorkoutSession.date.desc()).limit(limit)
        ).all()

        history = []
        for s in sessions:
            results = self.session.exec(select(ExerciseResult).where(ExerciseResult.session_id == s.id)).all()
            exercises_data = []
            for r in results:
                ex = self.session.get(Exercise, r.exercise_id)
                exercises_data.append({
                    "name": ex.name if ex else "Неизвестно",
                    "weight": r.weight_kg,
                    "sets": r.sets,
                    "reps": r.reps
                })
            history.append({
                "date": s.date.strftime("%d.%m.%Y %H:%M"),
                "notes": s.notes,
                "exercises": exercises_data
            })
        return history
import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from database.database import engine
from database.models import (
    User, WorkoutSession, ExerciseResult, Exercise
)

logger = logging.getLogger(__name__)


def get_or_create_user(telegram_id: int) -> User:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user


def save_workout_session(
        telegram_id: int,
        notes: str = "",
        workout_id: int | None = None
) -> int:
    with Session(engine) as session:
        user = get_or_create_user(telegram_id)

        new_session = WorkoutSession(
            user_id=user.id,
            workout_id=workout_id,
            notes=notes
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)
        return new_session.id


def add_exercise_result(
        session_id: int,
        exercise_name: str,
        weight_kg: float,
        sets: int,
        reps: int
) -> bool:
    with Session(engine) as session:
        # 1. Ищем упражнение по имени (или создаем, если его нет)
        exercise = session.exec(select(Exercise).where(Exercise.name == exercise_name)).first()
        if not exercise:
            exercise = Exercise(
                name=exercise_name,
                muscle_group="Не указано",
                technique="Описание появится позже"
            )
            session.add(exercise)
            session.commit()
            session.refresh(exercise)

        # 2. Сохраняем результат
        result = ExerciseResult(
            session_id=session_id,
            exercise_id=exercise.id,
            weight_kg=weight_kg,
            sets=sets,
            reps=reps
        )
        session.add(result)
        session.commit()
        return True


def get_workout_history(telegram_id: int, limit: int = 5) -> list[dict]:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            return []

        # Получаем последние сессии
        sessions = session.exec(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user.id)
            .order_by(WorkoutSession.date.desc())
            .limit(limit)
        ).all()

        history = []
        for s in sessions:
            # Подтягиваем результаты упражнений для этой сессии
            results = session.exec(
                select(ExerciseResult)
                .where(ExerciseResult.session_id == s.id)
            ).all()

            exercises_data = []
            for r in results:
                # Получаем название упражнения
                ex = session.get(Exercise, r.exercise_id)
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
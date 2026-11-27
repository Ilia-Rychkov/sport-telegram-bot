from datetime import timezone
from zoneinfo import ZoneInfo

from sqlmodel import Session, select
from database.models import User, WorkoutSession, ExerciseResult, Exercise, ExerciseFeedback
from backend.services.interfaces.workout_service import IWorkoutService

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")

class WorkoutService(IWorkoutService):
    def __init__(self, session: Session):
        self.session = session

    def _get_or_create_user(self, telegram_id: int) -> User:
        user = self.session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        if not user:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            self.session.flush()
        return user

    def save_workout_batch(self, telegram_id: int, exercises: list[dict], notes: str = "Запись через бота") -> int:
        """
        Сохраняет тренировку с несколькими упражнениями одной транзакцией.
        Возвращает ID созданной сессии.
        """
        try:
            # 1. Создаем пользователя и сессию
            user = self._get_or_create_user(telegram_id)
            workout = WorkoutSession(user_id=user.id, notes=notes)
            self.session.add(workout)
            self.session.flush()  # Получаем workout.id

            # 2. Для каждого упражнения добавляем результат
            for ex in exercises:
                exercise_name = ex.get("exercise")
                if not exercise_name:
                    continue

                exercise = self.session.exec(select(Exercise).where(Exercise.name == exercise_name)).first()
                if exercise is None:
                    exercise = Exercise(
                        name=exercise_name,
                        muscle_group="Не указано",
                        technique="Описание появится позже",
                    )
                    self.session.add(exercise)
                    self.session.flush()

                self.session.add(ExerciseResult(
                    session_id=workout.id,
                    exercise_id=exercise.id,
                    weight_kg=ex.get("weight") or 0.0,
                    sets=ex.get("sets") or 1,
                    reps=ex.get("reps") or 1,
                ))

            # 3. Сохраняем всё разом
            self.session.commit()
            return workout.id

        except Exception:
            self.session.rollback()
            raise

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
            feedback = self.session.exec(
                select(ExerciseFeedback).where(ExerciseFeedback.session_id == s.id)
                .order_by(ExerciseFeedback.position)
            ).all()
            recorded_at = s.date
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.replace(tzinfo=timezone.utc)
            moscow_date = recorded_at.astimezone(MOSCOW_TIMEZONE)
            history.append({
                "date": moscow_date.strftime("%d.%m.%Y %H:%M МСК"),
                "notes": s.notes,
                "exercises": exercises_data,
                "feedback": [
                    {"name": entry.exercise_name, "instructions": entry.instructions, "rating": entry.rating}
                    for entry in feedback
                ],
            })
        return history

    def get_latest_working_sets(self, telegram_id: int, exercise_names: tuple[str, ...]) -> dict:
        exercise_ids = {name: [] for name in exercise_names}
        canonical_names = {
            name.casefold().replace("ё", "е"): name for name in exercise_names
        }
        for exercise_id, name in self.session.exec(select(Exercise.id, Exercise.name)):
            normalized = " ".join(name.casefold().replace("ё", "е").split())
            if normalized in canonical_names:
                exercise_ids[canonical_names[normalized]].append(exercise_id)

        working_sets = {}
        for name, ids in exercise_ids.items():
            if not ids:
                continue
            statement = (
                select(ExerciseResult.weight_kg, ExerciseResult.reps)
                .join(WorkoutSession, WorkoutSession.id == ExerciseResult.session_id)
                .join(User, User.id == WorkoutSession.user_id)
                .where(User.telegram_id == telegram_id, ExerciseResult.exercise_id.in_(ids))
                .order_by(WorkoutSession.date.desc(), ExerciseResult.id.desc())
                .limit(1)
            )
            result = self.session.exec(statement).first()
            if result is not None:
                weight, reps = result
                working_sets[name] = {"weight": weight, "reps": reps}
        return working_sets

    def save_exercise_feedback(
        self, telegram_id: int, workout_key: str, position: int,
        exercise_name: str, instructions: str, rating: str,
    ) -> str:
        feedback = self.session.get(ExerciseFeedback, (workout_key, position))
        if feedback is not None:
            return feedback.rating

        user = self._get_or_create_user(telegram_id)
        session_id = self.session.exec(
            select(ExerciseFeedback.session_id)
            .join(WorkoutSession, WorkoutSession.id == ExerciseFeedback.session_id)
            .where(ExerciseFeedback.workout_key == workout_key, WorkoutSession.user_id == user.id)
            .limit(1)
        ).first()
        if session_id is None:
            workout = WorkoutSession(user_id=user.id, notes="Пошаговая тренировка")
            self.session.add(workout)
            self.session.flush()
            session_id = workout.id

        self.session.add(ExerciseFeedback(
            workout_key=workout_key,
            position=position,
            session_id=session_id,
            exercise_name=exercise_name,
            instructions=instructions,
            rating=rating,
        ))
        self.session.commit()
        return rating

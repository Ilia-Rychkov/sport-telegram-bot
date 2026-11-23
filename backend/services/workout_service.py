from sqlmodel import Session, select
from database.models import User, WorkoutSession, ExerciseResult, Exercise
from backend.services.interfaces.workout_service import IWorkoutService

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
            history.append({
                "date": s.date.strftime("%d.%m.%Y %H:%M"),
                "notes": s.notes,
                "exercises": exercises_data
            })
        return history

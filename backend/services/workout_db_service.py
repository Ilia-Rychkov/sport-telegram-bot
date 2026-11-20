from sqlmodel import Session
from database.database import engine
from backend.services.workout_service import WorkoutService

def get_workout_history(telegram_id: int, limit: int = 5) -> list[dict]:
    """Совместимость со старым кодом progress.py."""
    with Session(engine) as session:
        service = WorkoutService(session)
        return service.get_history(telegram_id, limit)
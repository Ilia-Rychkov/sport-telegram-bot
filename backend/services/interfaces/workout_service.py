from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class IWorkoutService(ABC):
    """Контракт для работы с тренировками в БД."""

    @abstractmethod
    def save_workout_batch(self, telegram_id: int, exercises: List[Dict], notes: str = "") -> int:
        """Сохраняет тренировку с несколькими упражнениями. Возвращает ID сессии."""
        pass

    @abstractmethod
    def get_history(self, telegram_id: int, limit: int = 5) -> List[Dict]:
        """Возвращает историю тренировок."""
        pass
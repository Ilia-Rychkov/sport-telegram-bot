from abc import ABC, abstractmethod
from typing import List, Dict, TypedDict


class PlannedExercise(TypedDict):
    name: str
    instructions: str


class IWorkoutGeneratorService(ABC):
    @abstractmethod
    async def generate_plan(
        self,
        profile: Dict,
        location: str,
        equipment: List[str] | None,
        muscle_group: str,
        history: List[Dict]
    ) -> list[PlannedExercise] | None:
        """Генерирует план тренировки на основе профиля и истории."""
        pass

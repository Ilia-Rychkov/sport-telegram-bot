from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class IWorkoutGeneratorService(ABC):
    @abstractmethod
    async def generate_plan(
        self,
        profile: Dict,
        location: str,
        equipment: List[str],
        muscle_group: str,
        history: List[Dict]
    ) -> Optional[str]:
        """Генерирует план тренировки на основе профиля и истории."""
        pass
from abc import ABC, abstractmethod
from typing import List, Optional

class INutritionService(ABC):
    """Контракт для работы с генерацией питания."""

    @abstractmethod
    async def generate_plan(
        self,
        target_calories: int,
        target_protein: int,
        target_fat: int,
        target_carbs: int,
        allergies: Optional[List[str]] = None,
        daily_budget: Optional[float] = None
    ) -> Optional[str]:
        """Генерирует план питания и возвращает текст."""
        pass
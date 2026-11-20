from abc import ABC, abstractmethod
from typing import Dict, Optional

class IWorkoutParserService(ABC):
    """Контракт для парсинга текста тренировок через ИИ."""

    @abstractmethod
    async def parse_workout(self, user_text: str) -> list[dict]:
        pass
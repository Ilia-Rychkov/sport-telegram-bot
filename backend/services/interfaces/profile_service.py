from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IProfileService(ABC):
    """Интерфейс для работы с профилем пользователя."""

    @abstractmethod
    def get_profile(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Загружает профиль из БД в виде словаря."""
        pass

    @abstractmethod
    def save_profile(self, telegram_id: int, profile_data: Dict[str, Any]) -> None:
        """Сохраняет или обновляет профиль в БД."""
        pass

    @abstractmethod
    def recalculate_norms(self, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Рассчитывает нормы калорий и БЖУ на основе данных профиля."""
        pass
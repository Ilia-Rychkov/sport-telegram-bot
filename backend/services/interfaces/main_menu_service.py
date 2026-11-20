from abc import ABC, abstractmethod
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup


class IMainMenuService(ABC):
    """Интерфейс для работы с главным меню."""

    @abstractmethod
    def get_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Возвращает основную клавиатуру бота."""
        pass

    @abstractmethod
    def get_welcome_text(self) -> str:
        """Возвращает приветственный текст для /start."""
        pass

    @abstractmethod
    def get_help_text(self) -> str:
        """Возвращает текст помощи."""
        pass

    @abstractmethod
    def get_unknown_text(self) -> str:
        """Возвращает текст для непонятных сообщений."""
        pass
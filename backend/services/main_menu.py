from backend.services.interfaces.main_menu_service import IMainMenuService
from bot.keyboards.main import get_main_menu_keyboard

class MainMenuService(IMainMenuService):

    def get_main_keyboard(self):
        return get_main_menu_keyboard()

    def get_welcome_text(self) -> str:
        return (
            "Привет! Я помогу следить за питанием, тренировками "
            "и прогрессом.\nВыбери раздел в меню:"
        )

    def get_help_text(self) -> str:
        return (
            "Выбери раздел с помощью кнопок внизу.\n"
            "Чтобы снова открыть главное меню, отправь /start."
        )

    def get_unknown_text(self) -> str:
        return (
            "Не понимаю эту команду или сообщение.\n"
            "/start — главное меню\n"
            "/cancel — отменить заполнение анкеты"
        )
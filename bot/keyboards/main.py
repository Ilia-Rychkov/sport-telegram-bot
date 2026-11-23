from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.labels import make_button

PROFILE_BUTTON = "Мой профиль"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                make_button(PROFILE_BUTTON),
                make_button("Питание"),
            ],
            [
                make_button("Тренировки"),
                make_button("Прогресс"),
            ],
            [make_button("Помощь")],
        ],
        resize_keyboard=True,
    )

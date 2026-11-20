from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Мой профиль"),
                KeyboardButton(text="Питание"),
            ],
            [
                KeyboardButton(text="Тренировки"),
                KeyboardButton(text="Прогресс"),
            ],
            [KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
    )

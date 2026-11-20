from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


main_menu = ReplyKeyboardMarkup(
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
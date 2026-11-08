from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


progress_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Записать вес"),
            KeyboardButton(text="График веса"),
        ],
        [KeyboardButton(text="История тренировок")],
        [KeyboardButton(text="Главное меню")],
    ],
    resize_keyboard=True,
)


PERIOD_OPTIONS = {
    "За неделю": 7,
    "За месяц": 30,
    "За 3 месяца": 90,
    "За всё время": None,
}


period_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="За неделю"),
            KeyboardButton(text="За месяц"),
        ],
        [
            KeyboardButton(text="За 3 месяца"),
            KeyboardButton(text="За всё время"),
        ],
        [KeyboardButton(text="Главное меню")],
    ],
    resize_keyboard=True,
)
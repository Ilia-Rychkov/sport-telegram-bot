from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.labels import make_button


progress_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            make_button("Записать вес"),
            make_button("График веса"),
        ],
        [make_button("История тренировок")],
        [make_button("Главное меню")],
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
            make_button("За неделю"),
            make_button("За месяц"),
        ],
        [
            make_button("За 3 месяца"),
            make_button("За всё время"),
        ],
        [make_button("Главное меню")],
    ],
    resize_keyboard=True,
)

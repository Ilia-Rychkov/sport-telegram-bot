from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


SEX_OPTIONS = ("Мужской", "Женский")

ACTIVITY_OPTIONS = (
    "Минимальная — преимущественно сидячий день",
    "Низкая — лёгкая активность 1–3 раза в неделю",
    "Средняя — активность 3–5 раз в неделю",
    "Высокая — активность 6–7 раз в неделю",
    "Очень высокая — тяжёлая работа или интенсивные нагрузки",
)

GOAL_OPTIONS = (
    "Снижение веса",
    "Набор мышечной массы",
    "Поддержание веса",
)

FITNESS_OPTIONS = (
    "Начинающий",
    "Средний",
    "Продвинутый",
)


def make_keyboard(options):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=option)]
            for option in options
        ],
        resize_keyboard=True,
    )
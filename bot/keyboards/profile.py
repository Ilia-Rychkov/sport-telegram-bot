from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.labels import make_button


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
            [make_button(option)]
            for option in options
        ],
        resize_keyboard=True,
    )

def get_edit_profile_keyboard():
    """Клавиатура для просмотра профиля."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [make_button("Заполнить"), make_button("Изменить")],
            [make_button("В главное меню")],
        ],
        resize_keyboard=True,
    )

def get_cancel_keyboard():
    """Добавляем кнопку 'Сохранить и выйти' к обычным опциям."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [make_button("Сохранить и выйти")],
            [make_button("Отмена")],
        ],
        resize_keyboard=True,
    )

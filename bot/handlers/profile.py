from html import escape
from math import isfinite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, KeyboardButton
from bot.keyboards.main import get_main_menu_keyboard
from backend.services.main_menu import MainMenuService
from backend.services.nutrition_service import NutritionService
from bot.handlers.nutrition import generate_and_send_plan
from bot.handlers.nutrition_allergies import get_allergy_keyboard


from backend.services.profile_service import ProfileService
from database.models import MAX_PROFILE_AGE, MIN_PROFILE_AGE
from bot.keyboards.profile import (
    ACTIVITY_OPTIONS, FITNESS_OPTIONS, GOAL_OPTIONS, SEX_OPTIONS,
    make_keyboard, get_edit_profile_keyboard, get_cancel_keyboard
)

router = Router()

class ProfileForm(StatesGroup):
    age = State()
    sex = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()
    fitness = State()
    editing = State()
    allergies_asking = State()
    allergies_text = State()
    daily_budget = State()

FIELDS = {
    "age": ("Возраст", "Сколько тебе лет? Введи целое число."),
    "sex": ("Пол", "Выбери пол:"),
    "height": ("Рост", "Введи рост в сантиметрах, например 178:"),
    "weight": ("Вес", "Введи вес в килограммах, например 71,5:"),
    "activity": ("Активность", "Выбери обычный уровень активности:"),
    "goal": ("Цель", "Выбери свою цель:"),
    "fitness": ("Подготовка", "Выбери уровень физической подготовки:"),
    "allergies": ("Аллергии", "Есть ли у тебя аллергии или продукты, которые не ешь?"),
    "daily_budget": (
        "Бюджет на день",
        "Сколько рублей в день ты готов тратить на питание? Введи 0, если лимита нет.",
    ),
}
OPTIONS = {
    "sex": SEX_OPTIONS,
    "activity": ACTIVITY_OPTIONS,
    "goal": GOAL_OPTIONS,
    "fitness": FITNESS_OPTIONS,
}
NUMBER_LIMITS = {
    "age": (MIN_PROFILE_AGE, MAX_PROFILE_AGE),
    "height": (100, 250),
    "weight": (30, 350),
    "daily_budget": (0, 100000),
}
FIELD_ORDER = list(FIELDS)
EDIT_OPTIONS = [title for title, _ in FIELDS.values()]


def format_value(field: str, value) -> str:
    if value is None or value == "":
        return "Не указано"
    if field == "height":
        return f"{value} см"
    if field == "weight":
        return f"{value} кг"
    if field == "daily_budget":
        if value == 0:
            return "Без лимита"
        return f"{value} ₽/день"
    return str(value)


async def show_summary(message: Message, state: FSMContext, profile_service: ProfileService, profile: dict):
    await state.set_state(None)
    lines = ["👤 <b>Твой профиль:</b>\n"]
    for field, (title, _) in FIELDS.items():
        value = profile.get(field)
        lines.append(f"{title}: {escape(format_value(field, value))}")

    #allergies = profile.get("allergies")
    #lines.append(f"Аллергии: {allergies if allergies else 'Не указано'}")

    norms = profile_service.recalculate_norms(profile)
    if norms:
        lines.append("\n📊 <b>Суточная норма:</b>")
        lines.append(f"🔥 Калории: {norms['calories']} ккал")
        lines.append(f"🥩 БЖУ: {norms['protein']} / {norms['fat']} / {norms['carbs']} г")
    else:
        lines.append("\n⚠️ <i>Заполни все поля, чтобы рассчитать нормы.</i>")

    await message.answer(
        "\n".join(lines),
        reply_markup=get_edit_profile_keyboard(),
        parse_mode="HTML"
    )


async def ask_field(message: Message, state: FSMContext, field: str):
    """Спрашивает конкретное поле, добавляя кнопку 'Сохранить и выйти'."""
    field_state = ProfileForm.allergies_asking if field == "allergies" else getattr(ProfileForm, field)
    await state.set_state(field_state)
    if field == "allergies":
        keyboard = get_allergy_keyboard()
        keyboard.keyboard.append([KeyboardButton(text="Сохранить и выйти")])
    elif field in OPTIONS:
        keyboard = make_keyboard(OPTIONS[field])
        keyboard.keyboard.append([KeyboardButton(text="Сохранить и выйти")])
    else:
        keyboard = get_cancel_keyboard()

    await message.answer(FIELDS[field][1], reply_markup=keyboard)


def get_first_unfilled_field(profile: dict) -> str | None:
    """Возвращает название первого незаполненного поля (в порядке FIELD_ORDER)."""
    for field in FIELD_ORDER:
        if profile.get(field) is None:
            return field
    return None


@router.message(ProfileForm(), Command("cancel"))
async def cancel_profile(message: Message, state: FSMContext, profile_service: ProfileService):
    await state.clear()
    profile = profile_service.get_profile(message.from_user.id) or {}
    await show_summary(message, state, profile_service, profile)


@router.message(F.text == "Мой профиль")
async def open_profile(message: Message, state: FSMContext, profile_service: ProfileService):
    await state.clear()
    profile = profile_service.get_profile(message.from_user.id) or {}
    await state.update_data(draft=profile.copy(), editing_field=None)
    await show_summary(message, state, profile_service, profile)


@router.message(F.text == "Заполнить")
async def start_filling(message: Message, state: FSMContext, profile_service: ProfileService):
    """Поочередно спрашивает все незаполненные поля."""
    profile = profile_service.get_profile(message.from_user.id) or {}
    draft = profile.copy()
    await state.update_data(draft=draft, editing_field=None)

    first_field = get_first_unfilled_field(draft)
    if first_field is None:
        await state.set_state(None)
        await message.answer(
            "🎉 У тебя уже заполнены все поля! Если хочешь что-то поменять — нажми «Изменить».",
            reply_markup=get_edit_profile_keyboard()
        )
        return

    await ask_field(message, state, first_field)


@router.message(F.text == "Изменить")
async def start_editing(message: Message, state: FSMContext):
    await state.set_state(ProfileForm.editing)
    await message.answer(
        "Что хочешь изменить?",
        reply_markup=make_keyboard(EDIT_OPTIONS + ["Отмена"]),
    )


@router.message(F.text == "В главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()

    # Используем сервис главного меню, чтобы получить текст и клавиатуру
    menu_service = MainMenuService()

    await message.answer(
        menu_service.get_welcome_text(),  # или просто "Главное меню:"
        reply_markup=menu_service.get_main_keyboard()
    )


@router.message(ProfileForm.editing, F.text, ~F.text.startswith("/"))
async def choose_field(message: Message, state: FSMContext, profile_service: ProfileService):
    if message.text == "Отмена":
        await state.clear()
        profile = profile_service.get_profile(message.from_user.id) or {}
        await show_summary(message, state, profile_service, profile)
        return

    for field, (title, _) in FIELDS.items():
        if message.text == title:
            draft = profile_service.get_profile(message.from_user.id) or {}
            await state.update_data(draft=draft, editing_field=field)
            await ask_field(message, state, field)
            return

    await message.answer("Выбери поле с помощью кнопок.")


@router.message(ProfileForm(), F.text == "Сохранить и выйти")
async def save_and_exit(message: Message, state: FSMContext, profile_service: ProfileService):
    data = await state.get_data()
    profile_service.save_profile(message.from_user.id, data.get("draft", {}))
    await state.clear()
    await message.answer(
        "✅ Данные сохранены!\nВернуться в главное меню: /start.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(ProfileForm.age, F.text)
@router.message(ProfileForm.sex, F.text)
@router.message(ProfileForm.height, F.text)
@router.message(ProfileForm.weight, F.text)
@router.message(ProfileForm.activity, F.text)
@router.message(ProfileForm.goal, F.text)
@router.message(ProfileForm.fitness, F.text)
@router.message(ProfileForm.daily_budget, F.text)
async def receive_answer(
    message: Message, state: FSMContext, profile_service: ProfileService, nutrition_service: NutritionService
):
    if message.text == "Отмена":
        await state.clear()
        profile = profile_service.get_profile(message.from_user.id) or {}
        await show_summary(message, state, profile_service, profile)
        return

    current_state = await state.get_state()
    field = current_state.split(":")[-1]
    text = message.text.strip()

    # Валидация
    if field in OPTIONS:
        if text not in OPTIONS[field]:
            await message.answer("Выбери один из вариантов на кнопках.")
            return
        value = text
    else:
        try:
            if field == "age":
                value = int(text)
            elif field == "daily_budget":
                value = float(text.replace(",", "."))
                if value < 0:
                    await message.answer("Бюджет не может быть отрицательным.")
                    return
            else:
                value = float(text.replace(",", "."))
        except ValueError:
            await message.answer(
                "Введи целое число." if field == "age" else "Введи число, например 71 или 71,5."
            )
            return

        minimum, maximum = NUMBER_LIMITS[field]
        if not isfinite(value) or not minimum <= value <= maximum:
            await message.answer(f"Допустимое значение: от {minimum} до {maximum}.")
            return

    await apply_profile_answer(message, state, profile_service, nutrition_service, field, value)


async def apply_profile_answer(
    message: Message,
    state: FSMContext,
    profile_service: ProfileService,
    nutrition_service: NutritionService,
    field: str,
    value: str | int | float,
):
    data = await state.get_data()
    draft = data.get("draft", {})
    draft[field] = value
    await state.update_data(draft=draft)

    # Если мы в режиме "Изменить" — сохраняем и показываем сводку
    if data.get("editing_field") is not None:
        await state.update_data(editing_field=None)
        profile_service.save_profile(message.from_user.id, {field: value})
        profile = profile_service.get_profile(message.from_user.id) or {}
        await show_summary(message, state, profile_service, profile)
        return

    # Иначе мы в режиме "Заполнить" — ищем следующее незаполненное поле
    next_field = get_first_unfilled_field(draft)
    if next_field is not None:
        await ask_field(message, state, next_field)
        return

    profile_service.save_profile(message.from_user.id, draft)
    if data.get("came_from_nutrition"):
        await state.clear()
        await generate_and_send_plan(message, state, profile_service, nutrition_service)
    else:
        await show_summary(message, state, profile_service, draft)




@router.message(ProfileForm.allergies_asking, F.text == "Нет аллергий")
async def profile_no_allergies(
    message: Message, state: FSMContext, profile_service: ProfileService, nutrition_service: NutritionService
):
    await apply_profile_answer(message, state, profile_service, nutrition_service, "allergies", "Нет")


@router.message(ProfileForm.allergies_asking, F.text == "Написать вручную")
async def profile_write_allergies(message: Message, state: FSMContext):
    await state.set_state(ProfileForm.allergies_text)
    await message.answer(
        "Напиши список продуктов через запятую (например: орехи, молоко, глютен):",
        reply_markup=make_keyboard(["Отмена"]),
    )


@router.message(ProfileForm.allergies_text, F.text, F.text != "Отмена")
async def profile_save_allergies(
    message: Message, state: FSMContext, profile_service: ProfileService, nutrition_service: NutritionService
):
    allergies = message.text.strip()
    if not allergies:
        await message.answer("Напиши список продуктов через запятую.")
        return
    await apply_profile_answer(message, state, profile_service, nutrition_service, "allergies", allergies)


@router.message(ProfileForm.allergies_asking, F.text == "Отмена")
@router.message(ProfileForm.allergies_text, F.text == "Отмена")
async def profile_cancel_allergies(message: Message, state: FSMContext, profile_service: ProfileService):
    await state.clear()
    profile = profile_service.get_profile(message.from_user.id) or {}
    await show_summary(message, state, profile_service, profile)

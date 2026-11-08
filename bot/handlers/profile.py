from bot.keyboards.main_menu import main_menu
import asyncio
import logging
from math import isfinite

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.services.profile_service import recalculate_profile_norms
from bot.keyboards.profile import (
    ACTIVITY_OPTIONS,
    FITNESS_OPTIONS,
    GOAL_OPTIONS,
    SEX_OPTIONS,
    make_keyboard,
)
from database.models import ProfileData
from database.profiles import get_profile, save_profile


logger = logging.getLogger(__name__)
router = Router()


class ProfileForm(StatesGroup):
    age = State()
    sex = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()
    fitness = State()
    confirmation = State()
    editing = State()


FIELDS = {
    "age": ("Возраст", "Сколько тебе лет? Введи целое число."),
    "sex": ("Пол", "Выбери пол:"),
    "height": ("Рост", "Введи рост в сантиметрах, например 178:"),
    "weight": ("Вес", "Введи вес в килограммах, например 71,5:"),
    "activity": ("Активность", "Выбери обычный уровень активности:"),
    "goal": ("Цель", "Выбери свою цель:"),
    "fitness": ("Подготовка", "Выбери уровень физической подготовки:"),
}

OPTIONS = {
    "sex": SEX_OPTIONS,
    "activity": ACTIVITY_OPTIONS,
    "goal": GOAL_OPTIONS,
    "fitness": FITNESS_OPTIONS,
}

NUMBER_LIMITS = {
    "age": (18, 100),
    "height": (100, 250),
    "weight": (30, 350),
}

FIELD_ORDER = list(FIELDS)
EDIT_OPTIONS = [title for title, question in FIELDS.values()]


async def ask_field(message: Message, state: FSMContext, field: str):
    await state.set_state(getattr(ProfileForm, field))

    if field in OPTIONS:
        keyboard = make_keyboard(OPTIONS[field])
    else:
        keyboard = ReplyKeyboardRemove()

    await message.answer(
        FIELDS[field][1],
        reply_markup=keyboard,
    )


async def show_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    lines = ["Проверь данные:\n"]

    for field, (title, question) in FIELDS.items():
        value = draft[field]

        if field == "height":
            value = f"{value} см"
        elif field == "weight":
            value = f"{value} кг"

        lines.append(f"{title}: {value}")

    # Считаем нормы по текущим данным, включая изменения.
    norms = recalculate_profile_norms(draft)

    if norms is not None:
        lines.append("\nТвоя суточная норма:")
        lines.append(f"Калории: {norms['calories']} ккал")
        lines.append(
            f"БЖУ: {norms['protein']} / "
            f"{norms['fat']} / {norms['carbs']} г"
        )

        warning = norms.get("metadata", {}).get("warning")
        if warning:
            lines.append(f"\n⚠️ {warning}")
    else:
        lines.append("\nНе удалось рассчитать нормы калорий.")

    await state.set_state(ProfileForm.confirmation)
    await message.answer(
        "\n".join(lines),
        reply_markup=make_keyboard(
            ("Подтвердить", "Изменить данные", "Отмена")
        ),
        parse_mode=None,
    )


@router.message(Command("cancel"))
@router.message(F.text == "Отмена")
async def cancel_profile(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "Заполнение отменено. Выбери раздел в меню.",
        reply_markup=main_menu,
    )


@router.message(F.text == "Мой профиль")
async def open_profile(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    try:
        profile = await asyncio.to_thread(
            get_profile,
            message.from_user.id,
        )
    except SQLAlchemyError:
        logger.exception("Не удалось получить профиль")
        await message.answer(
            "Не удалось загрузить профиль. Попробуй позже."
        )
        return

    await state.clear()

    if profile is not None:
        draft = profile.model_dump(
            mode="json",
            include=set(FIELD_ORDER),
        )

        await state.update_data(
            draft=draft,
            editing_field=None,
        )
        await show_summary(message, state)
        return

    await state.update_data(draft={}, editing_field=None)
    await message.answer(
        "Заполним анкету. Анкета доступна пользователям "
        "от 18 до 100 лет.\n"
        "Отменить заполнение можно командой /cancel."
    )
    await ask_field(message, state, "age")


@router.message(ProfileForm.confirmation, F.text == "Подтвердить")
async def confirm_profile(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    data = await state.get_data()

    try:
        profile_data = ProfileData.model_validate(
            data.get("draft", {})
        )
    except ValidationError:
        await message.answer(
            "В анкете есть некорректные данные. "
            "Нажми «Изменить данные» и проверь значения."
        )
        return

    try:
        await asyncio.to_thread(
            save_profile,
            message.from_user.id,
            profile_data,
        )
    except SQLAlchemyError:
        logger.exception("Не удалось сохранить профиль")
        await message.answer(
            "Не удалось сохранить профиль. "
            "Черновик остался — попробуй подтвердить ещё раз."
        )
        return

    profile = profile_data.model_dump(mode="json")
    norms = recalculate_profile_norms(profile)

    if norms is not None:
        profile["norms"] = norms

    await state.clear()
    await state.update_data(profile=profile)

    text = "Профиль сохранён!\n"

    if norms is not None:
        text += (
            f"\nТвоя норма: {norms['calories']} ккал\n"
            f"БЖУ: {norms['protein']} / "
            f"{norms['fat']} / {norms['carbs']} г\n"
        )

        warning = norms.get("metadata", {}).get("warning")
        if warning:
            text += f"\n⚠️ {warning}\n"
    else:
        text += "\nНе удалось рассчитать нормы калорий.\n"

        text += "\nВыбери раздел в главном меню."

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode=None,
    )


@router.message(ProfileForm.confirmation, F.text == "Изменить данные")
async def choose_field(message: Message, state: FSMContext):
    await state.set_state(ProfileForm.editing)
    await message.answer(
        "Что хочешь изменить?",
        reply_markup=make_keyboard(EDIT_OPTIONS + ["Отмена"]),
    )


@router.message(
    ProfileForm.editing,
    F.text,
    ~F.text.startswith("/"),
)
async def edit_field(message: Message, state: FSMContext):
    for field, (title, question) in FIELDS.items():
        if message.text == title:
            await state.update_data(editing_field=field)
            await ask_field(message, state, field)
            return

    await message.answer("Выбери поле с помощью кнопок.")


@router.message(ProfileForm.age, F.text, ~F.text.startswith("/"))
@router.message(ProfileForm.sex, F.text, ~F.text.startswith("/"))
@router.message(ProfileForm.height, F.text, ~F.text.startswith("/"))
@router.message(ProfileForm.weight, F.text, ~F.text.startswith("/"))
@router.message(ProfileForm.activity, F.text, ~F.text.startswith("/"))
@router.message(ProfileForm.goal, F.text, ~F.text.startswith("/"))
@router.message(ProfileForm.fitness, F.text, ~F.text.startswith("/"))
async def receive_answer(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None or message.text is None:
        return

    field = current_state.split(":")[-1]
    text = message.text.strip()

    if field in OPTIONS:
        if text not in OPTIONS[field]:
            await message.answer("Выбери один из вариантов на кнопках.")
            return

        value = text
    else:
        try:
            if field == "age":
                value = int(text)
            else:
                value = float(text.replace(",", "."))
        except ValueError:
            await message.answer(
                "Введи целое число."
                if field == "age"
                else "Введи число, например 71 или 71,5."
            )
            return

        minimum, maximum = NUMBER_LIMITS[field]

        if not isfinite(value) or not minimum <= value <= maximum:
            await message.answer(
                f"Допустимое значение: от {minimum} до {maximum}."
            )
            return

    data = await state.get_data()
    draft = data["draft"].copy()
    draft[field] = value
    await state.update_data(draft=draft)

    if data.get("editing_field") is not None:
        await state.update_data(editing_field=None)
        await show_summary(message, state)
        return

    next_index = FIELD_ORDER.index(field) + 1

    if next_index < len(FIELD_ORDER):
        await ask_field(message, state, FIELD_ORDER[next_index])
    else:
        await show_summary(message, state)


@router.message(ProfileForm(), ~F.text.startswith("/"))
async def unexpected_answer(message: Message):
    await message.answer(
        "Сейчас заполняем анкету. Ответь на текущий вопрос "
        "или отправь /cancel."
    )
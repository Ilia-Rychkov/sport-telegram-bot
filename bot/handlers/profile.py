from backend.services.profile_service import recalculate_profile_norms

from math import isfinite

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.profile import (
    ACTIVITY_OPTIONS,
    FITNESS_OPTIONS,
    GOAL_OPTIONS,
    SEX_OPTIONS,
    make_keyboard,
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
    confirmation = State()
    editing = State()


# Порядок заполнения, названия полей и вопросы.
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

# Это ограничения ввода для первой версии проекта.
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

    # НОВОЕ: Если в профиле уже есть рассчитанные нормы, показываем их
    profile = data.get("profile")
    if profile and "norms" in profile:
        norms = profile["norms"]
        lines.append("\n📊 **Твоя суточная норма:**")
        lines.append(f"🔥 Калории: {norms['calories']} ккал")
        lines.append(f"🥩 БЖУ: {norms['protein']} / {norms['fat']} / {norms['carbs']} г")

        if norms.get("metadata", {}).get("warning"):
            lines.append(f"\n⚠️ {norms['metadata']['warning']}")

    await state.set_state(ProfileForm.confirmation)
    await message.answer(
        "\n".join(lines),
        reply_markup=make_keyboard(("Подтвердить", "Изменить данные", "Отмена")),
        parse_mode="Markdown"  # Добавили, чтобы жирный шрифт работал
    )


@router.message(Command("cancel"))
@router.message(F.text == "Отмена")
async def cancel_profile(message: Message, state: FSMContext):
    # Удаляем черновик, сохраняя ранее подтверждённый профиль.
    data = await state.get_data()
    profile = data.get("profile")

    await state.clear()

    if profile is not None:
        await state.update_data(profile=profile)

    await message.answer(
        "Заполнение отменено. Отправь /start, чтобы открыть меню.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(F.text == "Мой профиль")
async def open_profile(message: Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile")

    if profile is not None:
        await state.update_data(
            draft=profile.copy(),
            editing_field=None,
        )
        await show_summary(message, state)
        return

    await state.update_data(draft={}, editing_field=None)
    await message.answer(
        "Заполним анкету. В этой версии анкета доступна "
        "для пользователей от 18 до 100 лет.\n"
        "Отменить заполнение можно командой /cancel."
    )
    await ask_field(message, state, "age")

@router.message(ProfileForm.confirmation, F.text == "Подтвердить")
async def confirm_profile(message: Message, state: FSMContext):
    data = await state.get_data()
    profile = data["draft"].copy()

    # 1. НОВОЕ: Считаем нормы на основе данных из черновика
    norms = recalculate_profile_norms(profile)

    # 2. Очищаем состояние и сохраняем профиль (как было)
    await state.clear()

    if norms:
        # 3. Если расчет успешен, добавляем нормы в профиль
        profile["norms"] = norms
        await state.update_data(profile=profile)

        # Формируем текст с предупреждением (если оно есть)
        warning_text = f"\n\n⚠️ {norms['metadata']['warning']}" if norms['metadata'].get('warning') else ""

        # 4. Отправляем пользователю красивое сообщение с цифрами
        await message.answer(
            f"✅ Данные подтверждены!\n\n"
            f"Твоя норма: {norms['calories']} ккал\n"
            f"БЖУ: {norms['protein']} / {norms['fat']} / {norms['carbs']} г{warning_text}\n\n"
            f"Для просмотра и изменения открой «Мой профиль».\n"
            f"Вернуться в главное меню: /start.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        # 5. Если калькулятор упал (например, ошибка в данных), не теряем профиль
        await state.update_data(profile=profile)
        await message.answer(
            "Данные подтверждены!\n"
            "Но не удалось рассчитать нормы калорий. Попробуйте изменить данные позже.\n"
            "Вернуться в главное меню: /start.",
            reply_markup=ReplyKeyboardRemove(),
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


@router.message(
    ProfileForm.age,
    F.text,
    ~F.text.startswith("/"),
)
@router.message(
    ProfileForm.sex,
    F.text,
    ~F.text.startswith("/"),
)
@router.message(
    ProfileForm.height,
    F.text,
    ~F.text.startswith("/"),
)
@router.message(
    ProfileForm.weight,
    F.text,
    ~F.text.startswith("/"),
)
@router.message(
    ProfileForm.activity,
    F.text,
    ~F.text.startswith("/"),
)
@router.message(
    ProfileForm.goal,
    F.text,
    ~F.text.startswith("/"),
)
@router.message(
    ProfileForm.fitness,
    F.text,
    ~F.text.startswith("/"),
)
async def receive_answer(message: Message, state: FSMContext):
    current_state = await state.get_state()
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


# Этот обработчик находится после остальных обработчиков анкеты.
# Он ловит фото, стикеры и неподходящие ответы на этапе подтверждения.
@router.message(
    ProfileForm(),
    ~F.text.startswith("/"),
)
async def unexpected_answer(message: Message):
    await message.answer(
        "Сейчас заполняем анкету. Ответь на текущий вопрос "
        "или отправь /cancel."
    )
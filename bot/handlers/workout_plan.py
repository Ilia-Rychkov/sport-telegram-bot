import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.handlers.nutrition import split_text
from bot.keyboards.main import get_main_menu_keyboard
from bot.keyboards.profile import make_keyboard
from backend.services.interfaces.workout_generator_service import IWorkoutGeneratorService
from backend.services.interfaces.profile_service import IProfileService
from backend.services.interfaces.workout_service import IWorkoutService

logger = logging.getLogger(__name__)
router = Router()

PLAN_PROFILE_FIELDS = {
    "sex": "пол",
    "age": "возраст",
    "weight": "вес",
    "height": "рост",
    "goal": "цель",
    "fitness": "уровень подготовки",
}


class WorkoutPlanForm(StatesGroup):
    asking_location = State()
    asking_equipment = State()
    asking_muscle_group = State()


@router.message(WorkoutPlanForm(), Command("cancel"))
@router.message(WorkoutPlanForm(), F.text == "Отмена")
async def cancel_workout_plan(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Составление плана отменено.", reply_markup=get_main_menu_keyboard())


@router.message(F.text == "Составить план")
async def start_workout_plan(message: Message, state: FSMContext, profile_service: IProfileService):
    if await get_plan_profile(message, state, profile_service) is None:
        return

    await state.set_state(WorkoutPlanForm.asking_location)
    await message.answer(
        "Где ты будешь тренироваться?",
        reply_markup=make_keyboard(["Дом", "Зал", "Улица", "Отмена"]),
    )


async def get_plan_profile(
    message: Message, state: FSMContext, profile_service: IProfileService,
) -> dict | None:
    profile = profile_service.get_profile(message.from_user.id) or {}
    missing = [label for field, label in PLAN_PROFILE_FIELDS.items() if not profile.get(field)]
    if missing:
        await state.clear()
        await message.answer(
            f"Чтобы составить план, заполни в профиле следующие поля: {', '.join(missing)}.",
            reply_markup=get_main_menu_keyboard(),
        )
        return None
    return profile


@router.message(WorkoutPlanForm.asking_location, F.text)
async def process_location(message: Message, state: FSMContext):
    if message.text not in ["Дом", "Зал", "Улица"]:
        await message.answer("Выбери из кнопок: Дом, Зал, Улица.")
        return

    await state.update_data(location=message.text)

    if message.text == "Дом":
        await state.set_state(WorkoutPlanForm.asking_equipment)
        await message.answer(
            "Какой инвентарь у тебя есть? (напиши через запятую: гантели, турник, коврик)\n"
            "Если ничего нет — напиши «Нет».",
            reply_markup=make_keyboard(["Отмена"]),
        )
    else:
        await state.update_data(equipment=None)
        await state.set_state(WorkoutPlanForm.asking_muscle_group)
        await message.answer(
            "Какую группу мышц хочешь тренировать?",
            reply_markup=make_keyboard(["Грудь", "Спина", "Ноги", "Плечи", "Руки", "Пресс", "Всё тело", "Отмена"]),
        )


@router.message(WorkoutPlanForm.asking_equipment, F.text)
async def process_equipment(message: Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        equipment = []
    else:
        equipment = [e.strip() for e in message.text.split(",") if e.strip()]

    await state.update_data(equipment=equipment)
    await state.set_state(WorkoutPlanForm.asking_muscle_group)
    await message.answer(
        "Какую группу мышц хочешь тренировать?",
        reply_markup=make_keyboard(["Грудь", "Спина", "Ноги", "Плечи", "Руки", "Пресс", "Всё тело", "Отмена"]),
    )


@router.message(WorkoutPlanForm.asking_muscle_group, F.text)
async def process_muscle_group(
    message: Message,
    state: FSMContext,
    profile_service: IProfileService,
    workout_service: IWorkoutService,
    workout_generator: IWorkoutGeneratorService
):
    profile = await get_plan_profile(message, state, profile_service)
    if profile is None:
        return

    await state.update_data(muscle_group=message.text)
    data = await state.get_data()

    thinking_msg = await message.answer("⏳ Составляю план тренировки...")

    history = workout_service.get_history(message.from_user.id, limit=3)

    plan = await workout_generator.generate_plan(
        profile=profile,
        location=data["location"],
        equipment=data["equipment"],
        muscle_group=data["muscle_group"],
        history=history
    )

    await thinking_msg.delete()
    await state.clear()

    if plan:
        for part in split_text(plan):
            try:
                await message.answer(part, parse_mode="HTML")
            except Exception:
                await message.answer(part)
        await message.answer("Выбери раздел в главном меню.", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer(
            "😔 Не удалось составить план. Попробуй позже.",
            reply_markup=get_main_menu_keyboard(),
        )

import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards.profile import make_keyboard
from backend.services.interfaces.workout_generator_service import IWorkoutGeneratorService
from backend.services.interfaces.profile_service import IProfileService
from backend.services.interfaces.workout_service import IWorkoutService

logger = logging.getLogger(__name__)
router = Router()


class WorkoutPlanForm(StatesGroup):
    asking_location = State()
    asking_equipment = State()
    asking_muscle_group = State()


@router.message(F.text == "Составить план")
async def start_workout_plan(message: Message, state: FSMContext, profile_service: IProfileService):
    profile = profile_service.get_profile(message.from_user.id)
    if not profile:
        await message.answer("Сначала заполни профиль (нажми «Мой профиль»).")
        return

    await state.set_state(WorkoutPlanForm.asking_location)
    await message.answer(
        "Где ты будешь тренироваться?",
        reply_markup=make_keyboard(["Дом", "Зал", "Улица"])
    )


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
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await state.update_data(equipment=[])
        await state.set_state(WorkoutPlanForm.asking_muscle_group)
        await message.answer(
            "Какую группу мышц хочешь тренировать?",
            reply_markup=make_keyboard(["Грудь", "Спина", "Ноги", "Плечи", "Руки", "Пресс", "Всё тело"])
        )


@router.message(WorkoutPlanForm.asking_equipment, F.text)
async def process_equipment(message: Message, state: FSMContext):
    if message.text.lower() == "нет":
        equipment = []
    else:
        equipment = [e.strip() for e in message.text.split(",") if e.strip()]

    await state.update_data(equipment=equipment)
    await state.set_state(WorkoutPlanForm.asking_muscle_group)
    await message.answer(
        "Какую группу мышц хочешь тренировать?",
        reply_markup=make_keyboard(["Грудь", "Спина", "Ноги", "Плечи", "Руки", "Пресс", "Всё тело"])
    )


@router.message(WorkoutPlanForm.asking_muscle_group, F.text)
async def process_muscle_group(
    message: Message,
    state: FSMContext,
    profile_service: IProfileService,
    workout_service: IWorkoutService,
    workout_generator: IWorkoutGeneratorService
):
    await state.update_data(muscle_group=message.text)
    data = await state.get_data()

    thinking_msg = await message.answer("⏳ Составляю план тренировки...")

    profile = profile_service.get_profile(message.from_user.id)
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
        from bot.handlers.nutrition import split_text
        for part in split_text(plan):
            try:
                await message.answer(part, parse_mode="HTML")
            except Exception:
                await message.answer(part)
    else:
        await message.answer("😔 Не удалось составить план. Попробуй позже.")
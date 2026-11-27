import logging
import re
from uuid import uuid4

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.exc import SQLAlchemyError

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

ASSESSMENT_QUESTIONS = {
    "pull_ups": "Сколько раз можешь подтянуться за один подход? Можно ввести 0.",
    "push_ups": "Сколько раз можешь отжаться за один подход? Можно ввести 0.",
    "run_1km": "За сколько обычно пробегаешь 1 км? Введи время как 6:30.",
}
GYM_EXERCISES = ("Жим лёжа", "Жим ногами")
SKIP_QUESTION = "Пропустить"
EXERCISE_RATINGS = {
    "easy": ("🙂", "Легко"),
    "fine": ("👌", "В самый раз"),
    "hard": ("😓", "Тяжело"),
    "failed": ("❌", "Не смог"),
}


class WorkoutPlanForm(StatesGroup):
    asking_location = State()
    asking_assessment = State()
    asking_equipment = State()
    asking_muscle_group = State()
    doing_exercise = State()


class GuidedWorkoutAction(CallbackData, prefix="guided_workout"):
    workout_key: str
    position: int
    action: str


@router.message(WorkoutPlanForm(), Command("cancel"))
@router.message(WorkoutPlanForm(), F.text == "Отмена")
async def cancel_workout_plan(message: Message, state: FSMContext):
    active = await state.get_state() == WorkoutPlanForm.doing_exercise.state
    await state.clear()
    response = "Тренировка остановлена." if active else "Составление плана отменено."
    await message.answer(response, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "Составить план")
async def start_workout_plan(message: Message, state: FSMContext, profile_service: IProfileService):
    if await get_plan_profile(message, state, profile_service) is None:
        return

    await state.clear()
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
async def process_location(
    message: Message,
    state: FSMContext,
    profile_service: IProfileService,
    workout_service: IWorkoutService,
):
    if message.text not in ["Дом", "Зал", "Улица"]:
        await message.answer("Выбери из кнопок: Дом, Зал, Улица.")
        return

    await state.update_data(location=message.text)
    profile = await get_plan_profile(message, state, profile_service)
    if profile is None:
        return

    saved_assessment = profile.get("training_assessment")
    assessment = dict(saved_assessment or {})
    questions = list(ASSESSMENT_QUESTIONS) if saved_assessment is None else []
    if message.text == "Зал" and not assessment.get("gym_completed"):
        known_sets = workout_service.get_latest_working_sets(message.from_user.id, GYM_EXERCISES)
        questions.extend(name for name in GYM_EXERCISES if name not in known_sets)
        assessment["gym_completed"] = True

    if questions:
        await state.set_state(WorkoutPlanForm.asking_assessment)
        await state.update_data(assessment=assessment, assessment_questions=questions)
        await ask_assessment_question(message, questions[0])
        return

    if assessment != saved_assessment:
        profile_service.save_profile(message.from_user.id, {"training_assessment": assessment})
    await continue_after_location(message, state, message.text)


async def ask_assessment_question(message: Message, question: str):
    prompt = ASSESSMENT_QUESTIONS.get(
        question,
        f"{question}. Если уже делаешь это упражнение, укажи рабочий вес и повторения. Например, 40 кг 8 повторений.",
    )
    await message.answer(prompt, reply_markup=make_keyboard([SKIP_QUESTION, "Отмена"]))


@router.message(WorkoutPlanForm.asking_assessment, F.text)
async def process_assessment_answer(
    message: Message, state: FSMContext, profile_service: IProfileService,
):
    data = await state.get_data()
    question, *remaining = data["assessment_questions"]
    assessment = dict(data["assessment"])
    answer = message.text.strip()

    if answer != SKIP_QUESTION:
        if question in ("pull_ups", "push_ups"):
            if not re.fullmatch(r"[0-9]{1,3}", answer):
                await message.answer("Введи целое число от 0 до 999 или нажми «Пропустить».")
                return
            assessment[question] = int(answer)
        elif question == "run_1km":
            if not re.fullmatch(r"[0-9]{1,3}:[0-5][0-9]", answer) or not any(
                int(part) for part in answer.split(":")
            ):
                await message.answer("Введи время в формате минуты:секунды, например 6:30.")
                return
            assessment[question] = answer
        else:
            match = re.fullmatch(
                r"([0-9]{1,4}(?:[.,][0-9]{1,2})?)"
                r"(?:\s*(?:кг\s*)?[xх×]\s*|\s*кг\s+|\s+)"
                r"([1-9][0-9]{0,2})(?:\s*(?:повторени[еяй]|повт\.?))?",
                answer.casefold(),
            )
            if not match:
                await message.answer("Напиши, например, «40 кг 8 повторений» или «40 8». Можно пропустить.")
                return
            weight, reps = match.groups()
            assessment[question] = {"weight": float(weight.replace(",", ".")), "reps": int(reps)}

    if remaining:
        await state.update_data(assessment=assessment, assessment_questions=remaining)
        await ask_assessment_question(message, remaining[0])
        return

    profile_service.save_profile(message.from_user.id, {"training_assessment": assessment})
    await continue_after_location(message, state, data["location"])


async def continue_after_location(message: Message, state: FSMContext, location: str):
    if location == "Дом":
        await state.set_state(WorkoutPlanForm.asking_equipment)
        await message.answer(
            "Какой инвентарь у тебя есть? (напиши через запятую: гантели, турник, коврик)\n"
            "Если ничего нет — напиши «Нет».",
            reply_markup=make_keyboard(["Отмена"]),
        )
    else:
        await state.update_data(equipment=None)
        await ask_muscle_group(message, state)


@router.message(WorkoutPlanForm.asking_equipment, F.text)
async def process_equipment(message: Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        equipment = []
    else:
        equipment = [e.strip() for e in message.text.split(",") if e.strip()]

    await state.update_data(equipment=equipment)
    await ask_muscle_group(message, state)


async def ask_muscle_group(message: Message, state: FSMContext):
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

    thinking_msg = await message.answer("⏳ Составляю план тренировки...", reply_markup=ReplyKeyboardRemove())

    history = workout_service.get_history(message.from_user.id, limit=3)
    if data["location"] == "Зал":
        assessment = profile.get("training_assessment") or {}
        manual_sets = {name: assessment[name] for name in GYM_EXERCISES if name in assessment}
        latest_sets = workout_service.get_latest_working_sets(message.from_user.id, GYM_EXERCISES)
        profile["gym_working_sets"] = {**manual_sets, **latest_sets}

    plan = await workout_generator.generate_plan(
        profile=profile,
        location=data["location"],
        equipment=data["equipment"],
        muscle_group=data["muscle_group"],
        history=history,
    )

    await thinking_msg.delete()
    if not plan:
        await state.clear()
        await message.answer(
            "😔 Не удалось составить план. Попробуй позже.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    workout = {"workout_key": uuid4().hex, "plan": plan, "position": 0, "rating": None}
    await state.set_data(workout)
    await state.set_state(WorkoutPlanForm.doing_exercise)
    await message.answer(exercise_text(workout), reply_markup=exercise_keyboard(workout), parse_mode=None)


def exercise_text(workout: dict) -> str:
    position = workout["position"]
    exercise = workout["plan"][position]
    text = f"Упражнение {position + 1} из {len(workout['plan'])}. {exercise['name']}\n\n{exercise['instructions']}"
    if workout["rating"] is not None:
        return f"{text}\n\nОценка сохранена. {workout['rating']}."
    return f"{text}\n\nКогда закончишь, оцени, как прошло упражнение."


def exercise_keyboard(workout: dict) -> InlineKeyboardMarkup:
    def button(action: str, label: str) -> InlineKeyboardButton:
        callback_data = GuidedWorkoutAction(
            workout_key=workout["workout_key"], position=workout["position"], action=action,
        ).pack()
        return InlineKeyboardButton(text=label, callback_data=callback_data)

    stop = button("stop", "⏹ Остановить тренировку")
    if workout["rating"] is not None:
        if workout["position"] + 1 == len(workout["plan"]):
            return InlineKeyboardMarkup(inline_keyboard=[[button("next", "✅ Завершить тренировку")]])
        return InlineKeyboardMarkup(inline_keyboard=[[button("next", "➡️ Следующее упражнение")], [stop]])

    ratings = [button(action, f"{emoji} {label}") for action, (emoji, label) in EXERCISE_RATINGS.items()]
    return InlineKeyboardMarkup(inline_keyboard=[ratings[:2], ratings[2:], [stop]])


@router.callback_query(GuidedWorkoutAction.filter())
async def process_guided_workout_action(
    callback: CallbackQuery,
    callback_data: GuidedWorkoutAction,
    state: FSMContext,
    workout_service: IWorkoutService,
):
    workout = await state.get_data()
    if (
        await state.get_state() != WorkoutPlanForm.doing_exercise.state
        or workout.get("workout_key") != callback_data.workout_key
        or workout.get("position") != callback_data.position
        or not isinstance(callback.message, Message)
    ):
        await callback.answer("Это упражнение уже не активно.")
        return

    message = callback.message
    action = callback_data.action
    position = workout["position"]
    rated = workout["rating"] is not None
    finished = action == "next" and rated and position + 1 == len(workout["plan"])
    if action == "stop" or finished:
        await state.clear()
        await callback.answer()
        await message.edit_reply_markup(reply_markup=None)
        response = "Тренировка остановлена." if action == "stop" else "Тренировка завершена."
        await message.answer(response, reply_markup=get_main_menu_keyboard())
        return

    if action == "next" and rated:
        workout.update(position=position + 1, rating=None)
    elif action in EXERCISE_RATINGS and not rated:
        exercise = workout["plan"][position]
        try:
            workout["rating"] = workout_service.save_exercise_feedback(
                callback.from_user.id, workout["workout_key"], position,
                exercise["name"], exercise["instructions"], EXERCISE_RATINGS[action][1],
            )
        except SQLAlchemyError:
            logger.exception("Не удалось сохранить оценку упражнения")
            await callback.answer("Не удалось сохранить оценку. Попробуй ещё раз.", show_alert=True)
            return
    else:
        await callback.answer("Выбери действие под упражнением.")
        return

    await message.edit_text(exercise_text(workout), reply_markup=exercise_keyboard(workout), parse_mode=None)
    await state.set_data(workout)
    await callback.answer()

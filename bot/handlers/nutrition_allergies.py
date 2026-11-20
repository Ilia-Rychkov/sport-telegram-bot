import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.services.profile_service import ProfileService
from backend.services.nutrition_service import NutritionService
from bot.keyboards.main import get_main_menu_keyboard
from bot.keyboards.profile import make_keyboard

logger = logging.getLogger(__name__)
router = Router()


class AllergyForm(StatesGroup):
    asking = State()
    waiting_for_text = State()


def get_allergy_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Нет аллергий")],
            [KeyboardButton(text="Написать вручную")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )


async def ask_for_allergies(message: Message, state: FSMContext):
    """Запускает опрос об аллергиях."""
    await state.set_state(AllergyForm.asking)
    await message.answer(
        "🍏 Прежде чем составить меню, скажи: есть ли у тебя аллергии или продукты, которые ты не ешь?\n"
        "Это важно для безопасности.",
        reply_markup=get_allergy_keyboard()
    )


@router.message(AllergyForm.asking, F.text == "Нет аллергий")
async def no_allergies(
    message: Message,
    state: FSMContext,
    profile_service: ProfileService,
    nutrition_service: NutritionService  # <-- Получаем сервис из middleware
):
    # 1. Загружаем профиль из БД
    profile = profile_service.get_profile(message.from_user.id)
    if not profile:
        await message.answer("Ошибка: профиль не найден. Заполни анкету заново через /start.")
        return

    # 2. Обновляем поле аллергий и сохраняем в БД
    profile_service.save_profile(message.from_user.id, {"allergies": "Нет"})

    await message.answer("Принято! Теперь составлю меню.", reply_markup=ReplyKeyboardRemove())

    # 3. Сбрасываем FSM и запускаем генерацию
    await state.clear()
    from bot.handlers.nutrition import generate_and_send_plan
    await generate_and_send_plan(message, state, profile_service, nutrition_service)


@router.message(AllergyForm.asking, F.text == "Написать вручную")
async def write_allergies_manually(message: Message, state: FSMContext):
    await state.set_state(AllergyForm.waiting_for_text)
    await message.answer(
        "Напиши список продуктов через запятую (например: орехи, молоко, глютен):",
        reply_markup=make_keyboard(["Отмена"]),
    )


@router.message(AllergyForm.waiting_for_text, F.text, F.text != "Отмена")
async def save_allergies_text(
    message: Message,
    state: FSMContext,
    profile_service: ProfileService,
    nutrition_service: NutritionService
):
    # 1. Загружаем профиль из БД
    profile = profile_service.get_profile(message.from_user.id)
    if not profile:
        await message.answer("Ошибка: профиль не найден. Заполни анкету заново через /start.")
        return

    # 2. Обновляем поле аллергий и сохраняем в БД
    profile_service.save_profile(message.from_user.id, {"allergies": message.text})

    await message.answer(f"Записал: {message.text}. Учту это при составлении меню!")

    # 3. Сбрасываем FSM и запускаем генерацию
    await state.clear()
    from bot.handlers.nutrition import generate_and_send_plan
    await generate_and_send_plan(message, state, profile_service, nutrition_service)


@router.message(AllergyForm.asking, F.text == "Отмена")
@router.message(AllergyForm.waiting_for_text, F.text == "Отмена")
async def cancel_allergy(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отменено. Возвращаюсь в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )

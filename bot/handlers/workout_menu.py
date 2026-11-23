from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext

from bot.keyboards.labels import make_button

router = Router()

def get_workout_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [make_button("Записать тренировку")],
            [make_button("Составить план")],
            [make_button("В главное меню")],
        ],
        resize_keyboard=True,
    )

@router.message(F.text == "Тренировки")
async def workout_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏋️ Раздел тренировок. Что хочешь сделать?",
        reply_markup=get_workout_menu()
    )

@router.message(F.text == "В главное меню")
async def back_to_main(message: Message, state: FSMContext):
    from bot.handlers.start import get_main_menu_keyboard
    await state.clear()
    await message.answer(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )

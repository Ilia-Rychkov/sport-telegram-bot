from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext

router = Router()

def get_workout_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Записать тренировку")],
            [KeyboardButton(text="Составить план")],
            [KeyboardButton(text="В главное меню")],
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
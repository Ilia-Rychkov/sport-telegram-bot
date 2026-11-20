import asyncio
import logging
from ai_service import parse_workout_text, generate_nutrition_plan

logging.basicConfig(level=logging.INFO)

# --- ТЕСТОВЫЕ КЕЙСЫ ДЛЯ ТРЕНИРОВОК ---
WORKOUT_CASES = [
    "Жим лежа 80 кг на 10 раз, 3 подхода", # Идеальный
    "Сделал приседания 100х5 4п",          # Сленг
    "Сегодня делал становую тягу. Вес 120, сделал 6 повторений в 4 подходах.", # Разговорный
    "Отжимания 3 по 20",                   # Без веса
    "Потягал железо, было тяжко",          # Мусор (должен вернуть None)
]

# --- ТЕСТОВЫЕ КЕЙСЫ ДЛЯ ПИТАНИЯ ---
NUTRITION_CASES = [
    {
        "desc": "Нормальный запрос (2000 ккал)",
        "params": {"target_calories": 2000, "target_protein": 150, "target_fat": 60, "target_carbs": 200, "allergies": []}
    },
    {
        "desc": "Запрос с аллергией (без лактозы)",
        "params": {"target_calories": 1800, "target_protein": 120, "target_fat": 50, "target_carbs": 180, "allergies": ["лактоза", "молоко"]}
    },
    {
        "desc": "Провокация: Очень низкая калорийность (1000 ккал)",
        "params": {"target_calories": 1000, "target_protein": 100, "target_fat": 30, "target_carbs": 50, "allergies": []}
    }
]

async def run_qa():
    print("=== ТЕСТИРОВАНИЕ ПАРСИНГА ТРЕНИРОВОК ===")
    for i, text in enumerate(WORKOUT_CASES, 1):
        print(f"\n[Тест {i}] Вход: {text}")
        result = await parse_workout_text(text)
        print(f"Выход: {result}")
        await asyncio.sleep(3) # Пауза, чтобы не превысить лимиты Google

    print("\n\n=== ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ ПИТАНИЯ ===")
    for i, case in enumerate(NUTRITION_CASES, 1):
        print(f"\n[Тест {i}] {case['desc']}")
        plan = await generate_nutrition_plan(**case['params'])
        if plan:
            print(f"Ответ (фрагмент): {plan[:150]}...\n")
        else:
            print("Ошибка генерации (None)\n")
        await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(run_qa())
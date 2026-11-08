import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Dict, Any

logger = logging.getLogger(__name__)

# Типы для строгой валидации
Sex = Literal["male", "female"]
Activity = Literal["low", "light", "moderate", "high", "very_high"]
Goal = Literal["maintain", "lose", "gain"]

# Константы из ТЗ
PAL_MAP = {
    "low": Decimal("1.20"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "high": Decimal("1.725"),
    "very_high": Decimal("1.90")
}

GOAL_FACTORS = {
    "maintain": Decimal("1.00"),
    "lose": Decimal("0.85"),  # Дефицит 15%
    "gain": Decimal("1.07")   # Профицит 7%
}

# Функция округления HALF_UP (математическое округление)
def round_half_up(value: Decimal, decimal_places: int) -> Decimal:
    if decimal_places == 0:
        quantizer = Decimal("1")
    else:
        quantizer = Decimal("1." + "0" * decimal_places)
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)

def calculate_nutrition(
    sex: Sex, age: int, height: float, weight: float, activity: Activity, goal: Goal
) -> Dict[str, Any]:
    """
    Рассчитывает калории и КБЖУ строго по спецификации из т2.
    Возвращает словарь с результатами и метаданными.
    """
    # Приводим к Decimal для точности
    w = Decimal(str(weight))
    h = Decimal(str(height))
    a = Decimal(str(age))

    # 1. Расчет RMR (Миффлин-Сан Жеор)
    if sex == "male":
        rmr = (Decimal("10") * w) + (Decimal("6.25") * h) - (Decimal("5") * a) + Decimal("5")
    elif sex == "female":
        rmr = (Decimal("10") * w) + (Decimal("6.25") * h) - (Decimal("5") * a) - Decimal("161")
    else:
        raise ValueError("Неверный пол")

    # 2. Расчет TDEE
    pal = PAL_MAP.get(activity)
    if not pal:
        raise ValueError("Неверная активность")
    tdee = rmr * pal

    # 3. Корректировка на цель
    factor = GOAL_FACTORS.get(goal)
    if factor is None:
        raise ValueError("Неверная цель")
    target_raw = tdee * factor

    # 4. Округление калорий до целого
    calories = round_half_up(target_raw, 0)

    # 5. Расчет БЖУ (20% / 30% / 50%)
    protein = round_half_up(calories * Decimal("0.20") / Decimal("4"), 1)
    fat = round_half_up(calories * Decimal("0.30") / Decimal("9"), 1)
    carbs = round_half_up(calories * Decimal("0.50") / Decimal("4"), 1)

    # Защита от слишком низкой калорийности (из исследования т1)
    warning = None
    # Устанавливаем безопасный порог: для женщин 1500, для мужчин 1800
    safe_minimum = 1500 if sex == "female" else 1800

    if calories < safe_minimum:
        warning = (
            f"Внимание: рассчитанная калорийность ({calories} ккал) ниже безопасного порога "
            f"({safe_minimum} ккал). Это может быть опасно для здоровья. "
            "Рекомендуется проконсультироваться с врачом."
        )
        logger.warning(f"Расчетная калорийность {calories} < {safe_minimum}.")

    return {
        "calories": int(calories),
        "protein": float(protein),
        "fat": float(fat),
        "carbs": float(carbs),
        "metadata": {
            "rmr": float(round_half_up(rmr, 2)),
            "tdee": float(round_half_up(tdee, 2)),
            "goal": goal,
            "warning": warning
        }
    }
import pytest
from backend.services.calculator import calculate_nutrition

# Тестовые данные из таблицы ТЗ
TEST_CASES = [
    # (ID, sex, age, height, weight, activity, goal, exp_cal, exp_p, exp_f, exp_c)
    ("T01", "female", 30, 165, 70, "moderate", "maintain", 2201, 110.1, 73.4, 275.1),
    ("T02", "female", 30, 165, 70, "moderate", "lose", 1871, 93.6, 62.4, 233.9),
    ("T03", "female", 30, 165, 70, "moderate", "gain", 2355, 117.8, 78.5, 294.4),
    ("T04", "male", 25, 180, 80, "low", "maintain", 2166, 108.3, 72.2, 270.8),
    ("T15", "female", 65, 155, 75, "low", "lose", 1257, 62.9, 41.9, 157.1),
]


# Декоратор parametrize позволяет запустить один тест для всех кейсов
@pytest.mark.parametrize("test_id, sex, age, height, weight, activity, goal, exp_cal, exp_p, exp_f, exp_c", TEST_CASES)
def test_calculate_nutrition(test_id, sex, age, height, weight, activity, goal, exp_cal, exp_p, exp_f, exp_c):
    """Проверяет калории и БЖУ для конкретного кейса из ТЗ."""
    result = calculate_nutrition(sex, age, height, weight, activity, goal)

    # Используем assert для проверки. Если не совпадет - pytest выдаст ошибку.
    assert result["calories"] == exp_cal, f"[{test_id}] Ошибка в калориях"
    assert result["protein"] == exp_p, f"[{test_id}] Ошибка в белках"
    assert result["fat"] == exp_f, f"[{test_id}] Ошибка в жирах"
    assert result["carbs"] == exp_c, f"[{test_id}] Ошибка в углеводах"


def test_warning_low_calories():
    """Проверяет, что при калорийности ниже 1200 выдается предупреждение (из ТЗ T15)."""
    result = calculate_nutrition("female", 65, 155, 75, "low", "lose")
    assert result["metadata"]["warning"] is not None
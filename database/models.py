from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
from enum import Enum


class Goal(str, Enum):
    LOSE_WEIGHT = "Снижение веса"
    GAIN_MUSCLE = "Набор мышечной массы"
    MAINTAIN_WEIGHT = "Поддержание веса"


class FitnessLevel(str, Enum):
    BEGINNER = "Начинающий"
    INTERMEDIATE = "Средний"
    ADVANCED = "Продвинутый"
def current_time():
    return datetime.now(timezone.utc)


class Sex(str, Enum):
    MALE = "Мужской"
    FEMALE = "Женский"


class ActivityLevel(str, Enum):
    MINIMAL = "Минимальная — преимущественно сидячий день"
    LOW = "Низкая — лёгкая активность 1–3 раза в неделю"
    MODERATE = "Средняя — активность 3–5 раз в неделю"
    HIGH = "Высокая — активность 6–7 раз в неделю"
    VERY_HIGH = "Очень высокая — тяжёлая работа или интенсивные нагрузки"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    telegram_id: int = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=current_time)


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)

    sex: Sex
    age: int = Field(ge=18, le=100)
    weight: float = Field(ge=30, le=350)
    height: float = Field(ge=100, le=250)

    activity: ActivityLevel
    goal: Goal
    fitness: FitnessLevel
class Recipe(SQLModel, table=True):
    __tablename__ = "recipes"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    ingredients: str
    instructions: str

    calories: float = Field(ge=0)
    protein: float = Field(ge=0)
    fat: float = Field(ge=0)
    carbs: float = Field(ge=0)
class Exercise(SQLModel, table=True):
    __tablename__ = "exercises"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    muscle_group: str
    technique: str
class Workout(SQLModel, table=True):
    __tablename__ = "workouts"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    goal: Goal
    fitness: FitnessLevel

class WorkoutExercise(SQLModel, table=True):
    __tablename__ = "workout_exercises"

    workout_id: int = Field(
        foreign_key="workouts.id",
        primary_key=True,
    )
    exercise_id: int = Field(
        foreign_key="exercises.id",
        primary_key=True,
    )

    position: int = Field(ge=1)
    sets: int = Field(ge=1)
    repetitions: int = Field(ge=1)
    rest_seconds: int = Field(default=60, ge=0)
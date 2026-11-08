from datetime import datetime, timezone, timedelta
from math import isfinite

from sqlmodel import Session, select

from database.database import engine
from database.models import Profile, User, WeightEntry


def add_weight(telegram_id: int, weight: float) -> WeightEntry:
    if not isfinite(weight) or not 30 <= weight <= 350:
        raise ValueError("Вес должен быть от 30 до 350 кг.")

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.telegram_id == telegram_id)
        ).first()

        if user is None:
            raise ValueError("Сначала заполни профиль.")

        profile = session.exec(
            select(Profile).where(Profile.user_id == user.id)
        ).first()

        if profile is None:
            raise ValueError("Сначала заполни профиль.")

        entry = WeightEntry(
            user_id=user.id,
            weight=weight,
        )

        # Обновляем текущий вес и добавляем измерение в историю.
        profile.weight = weight
        session.add(profile)
        session.add(entry)

        session.commit()
        session.refresh(entry)

        return entry
def get_weight_history(
    telegram_id: int,
    days: int | None = None,
) -> list[WeightEntry]:
    if days is not None and days <= 0:
        raise ValueError("Период должен быть положительным.")

    with Session(engine) as session:
        statement = (
            select(WeightEntry)
            .join(User, WeightEntry.user_id == User.id)
            .where(User.telegram_id == telegram_id)
        )

        if days is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            statement = statement.where(
                WeightEntry.recorded_at >= since
            )

        statement = statement.order_by(
            WeightEntry.recorded_at,
            WeightEntry.id,
        )

        return list(session.exec(statement).all())
def get_last_weight(telegram_id: int) -> WeightEntry | None:
    with Session(engine) as session:
        statement = (
            select(WeightEntry)
            .join(User, WeightEntry.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .order_by(
                WeightEntry.recorded_at.desc(),
                WeightEntry.id.desc(),
            )
            .limit(1)
        )

        return session.exec(statement).first()
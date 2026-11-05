from sqlmodel import Session, select

from database.database import engine
from database.models import Profile, User, ProfileData


def get_profile(telegram_id: int) -> Profile | None:
    with Session(engine) as session:
        statement = (
            select(Profile)
            .join(User, Profile.user_id == User.id)
            .where(User.telegram_id == telegram_id)
        )

        return session.exec(statement).first()
def save_profile(telegram_id: int, data: ProfileData) -> Profile:
    with Session(engine) as session:
        try:
            user = session.exec(
                select(User).where(User.telegram_id == telegram_id)
            ).first()

            if user is None:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.flush()

            profile = session.exec(
                select(Profile).where(Profile.user_id == user.id)
            ).first()

            if profile is None:
                profile = Profile(
                    user_id=user.id,
                    **data.model_dump(),
                )
            else:
                for field, value in data.model_dump().items():
                    setattr(profile, field, value)

            session.add(profile)
            session.commit()
            session.refresh(profile)

            return profile

        except Exception:
            session.rollback()
            raise
"""User lookup and public-profile serialization."""

from sqlalchemy import func, select

from app.extensions import db
from app.models import User, UserLocation


def find_user_by_email(email: str) -> User | None:
    """Find an account using the case-insensitive email identity."""
    return db.session.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )


def find_user_by_id(user_id: int) -> User | None:
    """Load a user from the current database state."""
    return db.session.scalar(
        select(User).where(User.id == user_id).execution_options(populate_existing=True)
    )


def public_user(user: User) -> dict[str, object]:
    """Serialize a user without exposing credential or lockout fields."""
    location_ids = db.session.scalars(
        select(UserLocation.location_id).where(UserLocation.user_id == user.id)
    ).all()
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "status": user.status.value,
        "locationIds": sorted(location_ids),
    }

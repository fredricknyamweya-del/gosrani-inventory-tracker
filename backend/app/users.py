"""User lookup and public-profile serialization."""

from sqlalchemy import func, select

from app.extensions import db
from app.models import User


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
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "status": user.status.value,
        "locationIds": sorted(link.location_id for link in user.location_links),
    }

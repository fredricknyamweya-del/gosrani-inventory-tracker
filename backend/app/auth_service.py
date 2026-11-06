"""Authentication business rules."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import User, UserStatus
from app.users import find_user_by_email

AuthResult = tuple[Literal["authenticated", "invalid", "locked"], User | None, int]


def authenticate(
    email: str,
    password: str,
    max_failures: int,
    lock_seconds: int,
) -> AuthResult:
    """Verify credentials and persist account lockout state."""
    user = find_user_by_email(email)
    if user is None:
        return "invalid", None, 0

    now = datetime.now(UTC)
    locked_until = user.locked_until
    if locked_until is not None:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until > now:
            return "locked", None, max(1, int((locked_until - now).total_seconds()))

    if user.status != UserStatus.ACTIVE:
        return "invalid", None, 0

    if not check_password_hash(user.password_hash, password):
        user.failed_logins += 1
        if user.failed_logins >= max_failures:
            user.locked_until = now + timedelta(seconds=lock_seconds)
            db.session.commit()
            return "locked", None, lock_seconds
        db.session.commit()
        return "invalid", None, 0

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    db.session.commit()
    return "authenticated", user, 0

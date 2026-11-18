from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.user import User
from app.utils.errors import ApiError


def get_current_user(user_id: str) -> User:
    user = User.active().filter_by(id=user_id).first()
    if user is None:
        raise ApiError("User not found", 404)
    return user


def update_current_user(user_id: str, payload: dict) -> User:
    user = get_current_user(user_id)
    email = payload.get("email")
    if email is not None and email != user.email:
        # The unique index also covers soft-deleted users; IntegrityError below handles that.
        if User.active().filter(User.email == email, User.id != user.id).first():
            raise ApiError("Email is already registered", 400)
    if "name" in payload:
        user.name = payload["name"]
    if email is not None:
        user.email = email
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Email is already registered", 400)
    return user

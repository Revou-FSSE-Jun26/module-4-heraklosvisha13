from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import User
from app.utils.errors import ApiError

# Checked when the email is unknown so response time does not reveal which emails exist.
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")


def register(payload: dict) -> User:
    # The unique index also covers soft-deleted users; the IntegrityError
    # handler below turns that case into the same 400.
    if User.active().filter_by(email=payload["email"]).first() is not None:
        raise ApiError("Email is already registered", 400)
    user = User(
        name=payload["name"],
        email=payload["email"],
        password_hash=generate_password_hash(payload["password"]),
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Email is already registered", 400)
    return user


def login(payload: dict) -> tuple[str, User]:
    user = User.active().filter_by(email=payload["email"]).first()
    hash_to_check = user.password_hash if user else _DUMMY_HASH
    valid = check_password_hash(hash_to_check, payload["password"])
    if user is None or not valid:
        raise ApiError("Invalid email or password", 401)
    return create_access_token(identity=user.id), user

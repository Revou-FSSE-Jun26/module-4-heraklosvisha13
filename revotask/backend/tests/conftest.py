"""Shared fixtures for the RevoTask API test suite.

Isolation: every test gets a brand new, empty in-memory SQLite database that is
created from the models and dropped afterwards. The suite never reads
DATABASE_URL, so it cannot touch the development or production database.
Set TEST_DATABASE_URL to run against another dedicated database instead.
"""
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask_jwt_extended import create_access_token  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import (  # noqa: E402
    Board,
    BoardMember,
    Card,
    Column,
    Comment,
    Notification,
    User,
)

PASSWORD = "password123"
# Cheap hash so fixtures stay fast; the auth tests exercise the real register flow.
_FAST_HASH = generate_password_hash(PASSWORD, method="pbkdf2:sha256:1000")


def _test_config() -> dict:
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256",
        "FRONTEND_URL": "http://localhost:3000",
    }
    if url.startswith("sqlite"):
        # One shared connection so the in-memory database is visible to every session.
        config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }
    return config


@pytest.fixture()
def app():
    app = create_app(_test_config())
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


# ---------------------------------------------------------------- factories

def make_user(name: str, email: str | None = None) -> User:
    user = User(
        name=name,
        email=email or f"{name.lower()}@example.com",
        password_hash=_FAST_HASH,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


def auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(identity=user.id)}"}


def make_board(owner: User, name: str = "Project", columns=("To Do", "Doing", "Done")) -> Board:
    """Create a board with `owner` as admin and columns ordered 1000, 2000, ..."""
    board = Board(name=name)
    _db.session.add(board)
    _db.session.flush()
    _db.session.add(BoardMember(board_id=board.id, user_id=owner.id, role="admin"))
    for index, column_name in enumerate(columns, start=1):
        _db.session.add(Column(board_id=board.id, name=column_name, order=index * 1000.0))
    _db.session.commit()
    return board


def add_member(board: Board, user: User, role: str = "member") -> BoardMember:
    member = BoardMember(board_id=board.id, user_id=user.id, role=role)
    _db.session.add(member)
    _db.session.commit()
    return member


def board_columns(board: Board) -> list[Column]:
    return Column.active().filter_by(board_id=board.id).order_by(Column.order).all()


def make_card(column: Column, title: str = "Task", order: float = 1000.0, **fields) -> Card:
    card = Card(column_id=column.id, title=title, order=order, **fields)
    _db.session.add(card)
    _db.session.commit()
    return card


def make_comment(card: Card, author: User, body: str = "A comment") -> Comment:
    comment = Comment(card_id=card.id, author_id=author.id, body=body)
    _db.session.add(comment)
    _db.session.commit()
    return comment


def make_notification(recipient: User, board: Board, type: str = "card_assigned", **fields):
    notification = Notification(
        recipient_id=recipient.id,
        board_id=board.id,
        type=type,
        message=fields.pop("message", "Something happened"),
        **fields,
    )
    _db.session.add(notification)
    _db.session.commit()
    return notification


# ---------------------------------------------------------------- scenario fixtures

@pytest.fixture()
def alice(app):
    """Board admin."""
    return make_user("Alice")


@pytest.fixture()
def bob(app):
    """Regular board member."""
    return make_user("Bob")


@pytest.fixture()
def carol(app):
    """Authenticated user who is NOT a member of the board."""
    return make_user("Carol")


@pytest.fixture()
def alice_h(alice):
    return auth_headers(alice)


@pytest.fixture()
def bob_h(bob):
    return auth_headers(bob)


@pytest.fixture()
def carol_h(carol):
    return auth_headers(carol)


@pytest.fixture()
def board(alice, bob):
    """Board with alice (admin) and bob (member), columns To Do / Doing / Done."""
    board = make_board(alice)
    add_member(board, bob)
    return board


@pytest.fixture()
def columns(board):
    return board_columns(board)


@pytest.fixture()
def card(columns):
    """A card in the first column."""
    return make_card(columns[0], title="Write tests")

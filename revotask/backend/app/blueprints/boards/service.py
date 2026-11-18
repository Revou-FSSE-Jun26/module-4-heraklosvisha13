from sqlalchemy import update

from app.extensions import db
from app.models.board import Board
from app.models.board_member import BoardMember
from app.models.card import Card
from app.models.column import Column
from app.models.comment import Comment
from app.models.mixins import utcnow
from app.utils.errors import ApiError
from app.utils.queries import get_active_or_404


def require_member(user_id: str, board_id: str, admin: bool = False) -> BoardMember:
    membership = BoardMember.active().filter_by(board_id=board_id, user_id=user_id).first()
    if membership is None or (admin and membership.role != "admin"):
        raise ApiError("You do not have access to this board", 403)
    return membership


def require_board_access(user_id: str, board_id: str, admin: bool = False) -> Board:
    """Load the board (404, also when soft-deleted), then check membership (403)."""
    board = get_active_or_404(Board, board_id, "Board")
    require_member(user_id, board.id, admin=admin)
    return board


def _with_role(board: Board, role: str) -> Board:
    board.role = role
    return board


def create_board(user_id: str, payload: dict) -> Board:
    board = Board(name=payload["name"])
    db.session.add(board)
    db.session.flush()
    db.session.add(BoardMember(board_id=board.id, user_id=user_id, role="admin"))
    db.session.commit()
    return _with_role(board, "admin")


def list_boards(user_id: str) -> list[Board]:
    rows = (
        db.session.query(Board, BoardMember.role)
        .join(BoardMember, BoardMember.board_id == Board.id)
        .filter(
            BoardMember.user_id == user_id,
            BoardMember.deleted_at.is_(None),
            Board.deleted_at.is_(None),
        )
        .order_by(Board.created_at)
        .all()
    )
    return [_with_role(board, role) for board, role in rows]


def get_board_detail(user_id: str, board_id: str) -> Board:
    """Constant queries: board, membership, columns, cards (assignee joined)."""
    board = get_active_or_404(Board, board_id, "Board")
    membership = require_member(user_id, board.id)
    columns = Column.active().filter_by(board_id=board.id).order_by(Column.order).all()
    cards_by_column: dict[str, list[Card]] = {c.id: [] for c in columns}
    if columns:
        cards = (
            Card.active()
            .filter(Card.column_id.in_(cards_by_column.keys()))
            .order_by(Card.order)
            .all()
        )
        for card in cards:
            cards_by_column[card.column_id].append(card)
    for column in columns:
        column.cards = cards_by_column[column.id]
    board.columns = columns
    return _with_role(board, membership.role)


def update_board(user_id: str, board_id: str, payload: dict) -> Board:
    board = get_active_or_404(Board, board_id, "Board")
    membership = require_member(user_id, board.id, admin=True)
    if not payload:
        raise ApiError("No fields to update", 400)
    board.name = payload["name"]
    db.session.commit()
    return _with_role(board, membership.role)


def delete_board(user_id: str, board_id: str) -> str:
    board = get_active_or_404(Board, board_id, "Board")
    require_member(user_id, board.id, admin=True)
    now = utcnow()
    column_ids = db.session.query(Column.id).filter(
        Column.board_id == board.id, Column.deleted_at.is_(None)
    )
    card_ids = db.session.query(Card.id).filter(
        Card.column_id.in_(column_ids), Card.deleted_at.is_(None)
    )
    for model, condition in (
        (Comment, Comment.card_id.in_(card_ids)),
        (Card, Card.column_id.in_(column_ids)),
        (Column, Column.board_id == board.id),
    ):
        db.session.execute(
            update(model)
            .where(condition, model.deleted_at.is_(None))
            .values(deleted_at=now)
            .execution_options(synchronize_session=False)
        )
    board.deleted_at = now
    db.session.commit()
    return board.id

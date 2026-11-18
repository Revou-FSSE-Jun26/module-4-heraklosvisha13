from sqlalchemy import update

from app.blueprints.boards import service as board_service
from app.extensions import db
from app.models.card import Card
from app.models.column import Column
from app.models.comment import Comment
from app.models.mixins import utcnow
from app.utils.errors import ApiError
from app.utils.ordering import needs_rebalance, next_order, rebalance
from app.utils.queries import get_active_or_404


def _load_column(user_id: str, column_id: str) -> Column:
    column = get_active_or_404(Column, column_id, "Column")
    board_service.require_board_access(user_id, column.board_id)
    return column


def create_column(user_id: str, board_id: str, payload: dict) -> Column:
    board = board_service.require_board_access(user_id, board_id)
    column = Column(
        board_id=board.id,
        name=payload["name"],
        order=next_order(Column, Column.board_id == board.id),
    )
    db.session.add(column)
    db.session.commit()
    return column


def update_column(user_id: str, column_id: str, payload: dict) -> Column:
    column = _load_column(user_id, column_id)
    if not payload:
        raise ApiError("No fields to update", 400)
    column.name = payload["name"]
    db.session.commit()
    return column


def delete_column(user_id: str, column_id: str) -> str:
    column = _load_column(user_id, column_id)
    now = utcnow()
    card_ids = db.session.query(Card.id).filter(
        Card.column_id == column.id, Card.deleted_at.is_(None)
    )
    db.session.execute(
        update(Comment)
        .where(Comment.card_id.in_(card_ids), Comment.deleted_at.is_(None))
        .values(deleted_at=now)
        .execution_options(synchronize_session=False)
    )
    db.session.execute(
        update(Card)
        .where(Card.column_id == column.id, Card.deleted_at.is_(None))
        .values(deleted_at=now)
        .execution_options(synchronize_session=False)
    )
    column.deleted_at = now
    db.session.commit()
    return column.id


def reorder_column(user_id: str, board_id: str, payload: dict) -> tuple[Column, list[dict]]:
    board = board_service.require_board_access(user_id, board_id)
    column = get_active_or_404(Column, payload["column_id"], "Column")
    if column.board_id != board.id:
        raise ApiError("Column does not belong to this board", 400)
    try:
        column.order = payload["order"]
        scope = Column.board_id == board.id
        rebalanced = []
        if needs_rebalance(Column, scope, column.id, column.order):
            rebalanced = rebalance(Column, scope, column.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return column, rebalanced

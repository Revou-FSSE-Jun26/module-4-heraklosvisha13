from sqlalchemy import func, or_

from app.blueprints.boards import service as board_service
from app.blueprints.notifications import service as notification_service
from app.extensions import db
from app.models.board import Board
from app.models.board_member import BoardMember
from app.models.card import Card
from app.models.column import Column
from app.models.comment import Comment
from app.models.mixins import utcnow
from app.models.user import User
from app.utils.errors import ApiError
from app.utils.ordering import needs_rebalance, next_order, rebalance
from app.utils.queries import get_active_or_404


def _last_column_id(board_id: str) -> str | None:
    last = (
        Column.active().filter_by(board_id=board_id).order_by(Column.order.desc()).first()
    )
    return last.id if last else None


def _load_card(user_id: str, card_id: str) -> Card:
    card = get_active_or_404(Card, card_id, "Card")
    board_service.require_board_access(user_id, card.column.board_id)
    return card


def _validate_assignee(board_id: str, assignee_id: str | None) -> None:
    if assignee_id is None:
        return
    member = (
        BoardMember.active().filter_by(board_id=board_id, user_id=assignee_id).first()
    )
    if member is None or User.active().filter_by(id=assignee_id).first() is None:
        raise ApiError("Assignee must be a member of this board", 400)


def _notify_assigned(actor_id: str, card: Card, board_id: str) -> None:
    actor = User.active().filter_by(id=actor_id).first()
    notification_service.notify_card_assigned(actor, card, board_id)


def create_card(user_id: str, column_id: str, payload: dict) -> Card:
    column = get_active_or_404(Column, column_id, "Column")
    board_service.require_board_access(user_id, column.board_id)
    assignee_id = payload.get("assignee_id")
    _validate_assignee(column.board_id, assignee_id)
    card = Card(
        column_id=column.id,
        title=payload["title"],
        description=payload.get("description"),
        assignee_id=assignee_id,
        due_date=payload.get("due_date"),
        created_by_id=user_id,
        order=next_order(Card, Card.column_id == column.id),
    )
    if _last_column_id(column.board_id) == column.id:
        card.completed_at = utcnow()  # D-09
    db.session.add(card)
    db.session.flush()
    _notify_assigned(user_id, card, column.board_id)
    db.session.commit()
    return card


def search_cards(user_id: str, board_id: str, q: str | None) -> list[Card]:
    board = board_service.require_board_access(user_id, board_id)
    query = (
        Card.active()
        .join(Column, Card.column_id == Column.id)
        .filter(Column.board_id == board.id, Column.deleted_at.is_(None))
    )
    q = (q or "").strip()
    if q:
        pattern = f"%{_escape_like(q)}%"
        query = query.filter(
            or_(
                Card.title.ilike(pattern, escape="\\"),
                Card.description.ilike(pattern, escape="\\"),
            )
        )
    return query.order_by(Card.order).all()


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_my_tasks(user_id: str) -> dict:
    filters = (
        Card.assignee_id == user_id,
        Card.deleted_at.is_(None),
        Column.deleted_at.is_(None),
        Board.deleted_at.is_(None),
        BoardMember.deleted_at.is_(None),
        BoardMember.user_id == user_id,
    )

    def joined(query):
        return (
            query.select_from(Card)
            .join(Column, Card.column_id == Column.id)
            .join(Board, Column.board_id == Board.id)
            .join(BoardMember, BoardMember.board_id == Board.id)
            .filter(*filters)
        )

    rows = (
        joined(
            db.session.query(
                Card.id,
                Card.title,
                Board.id,
                Board.name,
                Column.name,
                Card.due_date,
                Card.completed_at,
            )
        )
        .order_by(Card.due_date.asc().nulls_last(), Card.created_at)
        .all()
    )
    total, completed = joined(
        db.session.query(func.count(Card.id), func.count(Card.completed_at))
    ).one()
    return {
        "items": [
            {
                "id": r[0],
                "title": r[1],
                "board_id": r[2],
                "board_name": r[3],
                "column_name": r[4],
                "due_date": r[5],
                "completed_at": r[6],
            }
            for r in rows
        ],
        "total": total,
        "completed": completed,
        "open": total - completed,
    }


def get_card_detail(user_id: str, card_id: str) -> Card:
    card = _load_card(user_id, card_id)
    comments = (
        Comment.active().filter_by(card_id=card.id).order_by(Comment.created_at).all()
    )
    creator = (
        User.active().filter_by(id=card.created_by_id).first()
        if card.created_by_id
        else None
    )
    activity = [
        {
            "type": "card_created",
            "actor_id": creator.id if creator else None,
            "actor_name": creator.name if creator else None,
            "created_at": card.created_at,
        }
    ]
    if card.completed_at is not None:
        activity.append(
            {
                "type": "card_completed",
                "actor_id": None,
                "actor_name": None,
                "created_at": card.completed_at,
            }
        )
    for comment in comments:
        activity.append(
            {
                "type": "comment_added",
                "actor_id": comment.author_id,
                "actor_name": comment.author.name if comment.author else None,
                "created_at": comment.created_at,
            }
        )
    activity.sort(key=lambda a: a["created_at"], reverse=True)
    card.comments = comments
    card.activity = activity[:10]
    return card


def update_card(user_id: str, card_id: str, payload: dict) -> Card:
    card = _load_card(user_id, card_id)
    if not payload:
        raise ApiError("No fields to update", 400)
    board_id = card.column.board_id
    if "assignee_id" in payload:
        _validate_assignee(board_id, payload["assignee_id"])
    previous_assignee = card.assignee_id
    for key in ("title", "description", "due_date", "assignee_id"):
        if key in payload:
            setattr(card, key, payload[key])
    if card.assignee_id != previous_assignee:
        _notify_assigned(user_id, card, board_id)
    db.session.commit()
    return card


def delete_card(user_id: str, card_id: str) -> str:
    card = _load_card(user_id, card_id)
    card.soft_delete()
    db.session.commit()
    return card.id


def move_card(user_id: str, card_id: str, payload: dict) -> tuple[Card, list[dict]]:
    card = _load_card(user_id, card_id)
    source_board_id = card.column.board_id
    target = get_active_or_404(Column, payload["column_id"], "Column")
    if target.board_id != source_board_id:
        raise ApiError("Cannot move a card to another board", 400)
    try:
        column_changed = card.column_id != target.id
        card.column_id = target.id
        card.order = payload["order"]
        if column_changed:
            if target.id == _last_column_id(source_board_id):
                if card.completed_at is None:
                    card.completed_at = utcnow()
            else:
                card.completed_at = None
        scope = Card.column_id == target.id
        rebalanced = []
        if needs_rebalance(Card, scope, card.id, card.order):
            rebalanced = rebalance(Card, scope, card.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return card, rebalanced

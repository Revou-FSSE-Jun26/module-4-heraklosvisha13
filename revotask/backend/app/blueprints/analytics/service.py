from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func

from app.blueprints.boards import service as board_service
from app.extensions import db
from app.models.board_member import BoardMember
from app.models.card import Card
from app.models.column import Column
from app.models.comment import Comment
from app.models.mixins import utcnow
from app.models.user import User


def week_start(now: datetime) -> datetime:
    """Monday 00:00 UTC of the week containing `now`."""
    now = now.astimezone(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def cards_per_column(board_id: str) -> list[dict]:
    rows = (
        db.session.query(Column.id, Column.name, func.count(Card.id))
        .outerjoin(Card, and_(Card.column_id == Column.id, Card.deleted_at.is_(None)))
        .filter(Column.board_id == board_id, Column.deleted_at.is_(None))
        .group_by(Column.id, Column.name, Column.order)
        .order_by(Column.order)
        .all()
    )
    return [{"column_id": r[0], "name": r[1], "count": r[2]} for r in rows]


def completed_this_week(board_id: str, start: datetime) -> int:
    return (
        db.session.query(func.count(Card.id))
        .join(Column, Card.column_id == Column.id)
        .filter(
            Column.board_id == board_id,
            Column.deleted_at.is_(None),
            Card.deleted_at.is_(None),
            Card.completed_at >= start,
        )
        .scalar()
    )


def member_activity(board_id: str, start: datetime) -> list[dict]:
    active_cards = (
        db.session.query(Card.id, Card.assignee_id, Card.completed_at)
        .join(Column, Card.column_id == Column.id)
        .filter(
            Column.board_id == board_id,
            Column.deleted_at.is_(None),
            Card.deleted_at.is_(None),
        )
        .subquery()
    )
    assigned = (
        db.session.query(active_cards.c.assignee_id.label("uid"), func.count().label("n"))
        .group_by(active_cards.c.assignee_id)
        .subquery()
    )
    done = (
        db.session.query(active_cards.c.assignee_id.label("uid"), func.count().label("n"))
        .filter(active_cards.c.completed_at >= start)
        .group_by(active_cards.c.assignee_id)
        .subquery()
    )
    commented = (
        db.session.query(Comment.author_id.label("uid"), func.count().label("n"))
        .join(active_cards, Comment.card_id == active_cards.c.id)
        .filter(Comment.deleted_at.is_(None))
        .group_by(Comment.author_id)
        .subquery()
    )
    rows = (
        db.session.query(
            User.id,
            User.name,
            func.coalesce(assigned.c.n, 0),
            func.coalesce(done.c.n, 0),
            func.coalesce(commented.c.n, 0),
        )
        .join(BoardMember, BoardMember.user_id == User.id)
        .outerjoin(assigned, assigned.c.uid == User.id)
        .outerjoin(done, done.c.uid == User.id)
        .outerjoin(commented, commented.c.uid == User.id)
        .filter(BoardMember.board_id == board_id, BoardMember.deleted_at.is_(None))
        .order_by(User.name)
        .all()
    )
    return [
        {
            "user_id": r[0],
            "name": r[1],
            "assigned_count": r[2],
            "completed_this_week": r[3],
            "comments_count": r[4],
        }
        for r in rows
    ]


def get_analytics(user_id: str, board_id: str, now: datetime | None = None) -> dict:
    board = board_service.require_board_access(user_id, board_id, admin=True)
    start = week_start(now or utcnow())
    return {
        "cards_per_column": cards_per_column(board.id),
        "completed_this_week": {
            "count": completed_this_week(board.id, start),
            "week_start": start.isoformat(),
        },
        "member_activity": member_activity(board.id, start),
    }

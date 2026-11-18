import math

from sqlalchemy import func, update

from app.extensions import db
from app.models.card import Card
from app.models.mixins import utcnow
from app.models.notification import Notification
from app.models.user import User
from app.utils.errors import ApiError
from app.utils.queries import get_active_or_404


def notify(
    recipient_id: str | None,
    actor_id: str | None,
    board_id: str,
    card_id: str | None,
    type: str,
    message: str,
) -> Notification | None:
    """Add a notification to the session without committing.

    The caller commits, so the notification and the triggering action are stored
    together. Nothing is added when the recipient is the actor.
    """
    if recipient_id is None or recipient_id == actor_id:
        return None
    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        board_id=board_id,
        card_id=card_id,
        type=type,
        message=message[:255],
    )
    db.session.add(notification)
    return notification


def _actor_name(actor: User | None) -> str:
    return actor.name if actor else "Someone"


def notify_card_assigned(actor: User | None, card: Card, board_id: str) -> None:
    notify(
        card.assignee_id,
        actor.id if actor else None,
        board_id,
        card.id,
        "card_assigned",
        f'{_actor_name(actor)} assigned you to "{card.title}"',
    )


def notify_comment_added(actor: User | None, card: Card, board_id: str) -> None:
    notify(
        card.assignee_id,
        actor.id if actor else None,
        board_id,
        card.id,
        "comment_added",
        f'{_actor_name(actor)} commented on "{card.title}"',
    )


def list_notifications(user_id: str, page: int, per_page: int) -> dict:
    base = Notification.active().filter(Notification.recipient_id == user_id)
    total = base.count()
    items = (
        base.order_by(Notification.created_at.desc(), Notification.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )
    unread_count = base.filter(Notification.read_at.is_(None)).count()
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": math.ceil(total / per_page),
        "unread_count": unread_count,
    }


def mark_read(user_id: str, notification_id: str) -> Notification:
    notification = get_active_or_404(Notification, notification_id, "Notification")
    if notification.recipient_id != user_id:
        raise ApiError("You do not have access to this notification", 403)
    if notification.read_at is None:
        notification.read_at = utcnow()
        db.session.commit()
    return notification


def mark_all_read(user_id: str) -> int:
    result = db.session.execute(
        update(Notification)
        .where(
            Notification.recipient_id == user_id,
            Notification.read_at.is_(None),
            Notification.deleted_at.is_(None),
        )
        .values(read_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    db.session.commit()
    return result.rowcount

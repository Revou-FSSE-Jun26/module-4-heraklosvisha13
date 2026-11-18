from app.blueprints.boards import service as board_service
from app.blueprints.notifications import service as notification_service
from app.extensions import db
from app.models.card import Card
from app.models.comment import Comment
from app.models.user import User
from app.utils.errors import ApiError
from app.utils.queries import get_active_or_404


def _load_card(user_id: str, card_id: str) -> Card:
    card = get_active_or_404(Card, card_id, "Card")
    board_service.require_board_access(user_id, card.column.board_id)
    return card


def list_comments(user_id: str, card_id: str) -> list[Comment]:
    card = _load_card(user_id, card_id)
    return Comment.active().filter_by(card_id=card.id).order_by(Comment.created_at).all()


def create_comment(user_id: str, card_id: str, payload: dict) -> Comment:
    card = _load_card(user_id, card_id)
    comment = Comment(card_id=card.id, author_id=user_id, body=payload["body"])
    db.session.add(comment)
    db.session.flush()
    if card.assignee_id:
        actor = User.active().filter_by(id=user_id).first()
        notification_service.notify_comment_added(actor, card, card.column.board_id)
    db.session.commit()
    return comment


def _load_own_comment(user_id: str, comment_id: str) -> Comment:
    comment = get_active_or_404(Comment, comment_id, "Comment")
    card = get_active_or_404(Card, comment.card_id, "Card")
    board_service.require_board_access(user_id, card.column.board_id)
    if comment.author_id != user_id:
        raise ApiError("Only the author can modify this comment", 403)
    return comment


def update_comment(user_id: str, comment_id: str, payload: dict) -> Comment:
    comment = _load_own_comment(user_id, comment_id)
    if not payload:
        raise ApiError("No fields to update", 400)
    comment.body = payload["body"]
    db.session.commit()
    return comment


def delete_comment(user_id: str, comment_id: str) -> str:
    comment = _load_own_comment(user_id, comment_id)
    comment.soft_delete()
    db.session.commit()
    return comment.id

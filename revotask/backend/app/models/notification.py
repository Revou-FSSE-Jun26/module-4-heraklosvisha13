from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid

NOTIFICATION_TYPES = ("card_assigned", "comment_added", "board_member_added")


class Notification(AuditMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    recipient_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    actor_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    board_id = db.Column(db.String(36), db.ForeignKey("boards.id"), nullable=False)
    card_id = db.Column(db.String(36), db.ForeignKey("cards.id"), nullable=True)
    type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "type IN ('card_assigned', 'comment_added', 'board_member_added')",
            name="ck_notifications_type",
        ),
    )

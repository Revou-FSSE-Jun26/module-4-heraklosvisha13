from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid


class Card(AuditMixin, db.Model):
    __tablename__ = "cards"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    column_id = db.Column(db.String(36), db.ForeignKey("columns.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assignee_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date = db.Column(db.DateTime(timezone=True), nullable=True)
    order = db.Column(db.Float, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    assignee = db.relationship("User", foreign_keys=[assignee_id], lazy="joined")
    column = db.relationship("Column", lazy="joined")

    __table_args__ = (db.Index("ix_cards_column_id_order", "column_id", "order"),)

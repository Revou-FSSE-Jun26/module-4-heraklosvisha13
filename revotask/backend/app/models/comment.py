from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid


class Comment(AuditMixin, db.Model):
    __tablename__ = "comments"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    card_id = db.Column(db.String(36), db.ForeignKey("cards.id"), nullable=False, index=True)
    author_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)  # 1..2000 chars, enforced by schema

    author = db.relationship("User", lazy="joined")

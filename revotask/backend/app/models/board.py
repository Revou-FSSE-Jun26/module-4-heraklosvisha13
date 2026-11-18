from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid


class Board(AuditMixin, db.Model):
    __tablename__ = "boards"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    name = db.Column(db.String(120), nullable=False)

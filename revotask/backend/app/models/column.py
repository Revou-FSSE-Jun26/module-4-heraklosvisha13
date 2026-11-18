from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid


class Column(AuditMixin, db.Model):
    __tablename__ = "columns"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    board_id = db.Column(db.String(36), db.ForeignKey("boards.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    order = db.Column(db.Float, nullable=False)

    __table_args__ = (db.Index("ix_columns_board_id_order", "board_id", "order"),)

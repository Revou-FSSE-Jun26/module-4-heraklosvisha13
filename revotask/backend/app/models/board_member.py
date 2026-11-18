from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid


class BoardMember(AuditMixin, db.Model):
    __tablename__ = "board_members"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    board_id = db.Column(db.String(36), db.ForeignKey("boards.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False, default="member")  # "member" | "admin"

    user = db.relationship("User", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("board_id", "user_id", name="uq_board_members_board_user"),
        db.CheckConstraint("role IN ('member', 'admin')", name="ck_board_members_role"),
    )

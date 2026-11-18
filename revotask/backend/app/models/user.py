from app.extensions import db
from app.models.mixins import AuditMixin, new_uuid


class User(AuditMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)  # stored lowercase
    password_hash = db.Column(db.String(255), nullable=False)

from flask import Blueprint, request

from app.blueprints.auth import service
from app.blueprints.auth.schema import LoginSchema, RegisterSchema
from app.blueprints.users.schema import UserPublicSchema
from app.utils.responses import success_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/api/auth/register")
def register():
    payload = RegisterSchema().load(request.get_json(silent=True) or {})
    user = service.register(payload)
    return success_response(UserPublicSchema().dump(user), 201)


@auth_bp.post("/api/auth/login")
def login():
    payload = LoginSchema().load(request.get_json(silent=True) or {})
    token, user = service.login(payload)
    return success_response(
        {"access_token": token, "user": UserPublicSchema().dump(user)}
    )

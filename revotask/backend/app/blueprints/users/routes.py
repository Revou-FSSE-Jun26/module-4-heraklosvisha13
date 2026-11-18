from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.users import service
from app.blueprints.users.schema import UserProfileSchema, UserUpdateSchema
from app.utils.responses import success_response

users_bp = Blueprint("users", __name__)


@users_bp.get("/api/users/me")
@jwt_required()
def get_me():
    user = service.get_current_user(get_jwt_identity())
    return success_response(UserProfileSchema().dump(user))


@users_bp.patch("/api/users/me")
@jwt_required()
def update_me():
    payload = UserUpdateSchema().load(request.get_json(silent=True) or {})
    user = service.update_current_user(get_jwt_identity(), payload)
    return success_response(UserProfileSchema().dump(user))

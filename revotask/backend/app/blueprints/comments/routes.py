from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.comments import service
from app.blueprints.comments.schema import (
    CommentCreateSchema,
    CommentSchema,
    CommentUpdateSchema,
)
from app.utils.responses import success_response

comments_bp = Blueprint("comments", __name__)


@comments_bp.get("/api/cards/<card_id>/comments")
@jwt_required()
def list_comments(card_id):
    comments = service.list_comments(get_jwt_identity(), card_id)
    return success_response(CommentSchema(many=True).dump(comments))


@comments_bp.post("/api/cards/<card_id>/comments")
@jwt_required()
def create_comment(card_id):
    payload = CommentCreateSchema().load(request.get_json(silent=True) or {})
    comment = service.create_comment(get_jwt_identity(), card_id, payload)
    return success_response(CommentSchema().dump(comment), 201)


@comments_bp.patch("/api/comments/<comment_id>")
@jwt_required()
def update_comment(comment_id):
    payload = CommentUpdateSchema().load(request.get_json(silent=True) or {}, partial=True)
    comment = service.update_comment(get_jwt_identity(), comment_id, payload)
    return success_response(CommentSchema().dump(comment))


@comments_bp.delete("/api/comments/<comment_id>")
@jwt_required()
def delete_comment(comment_id):
    deleted_id = service.delete_comment(get_jwt_identity(), comment_id)
    return success_response({"id": deleted_id})

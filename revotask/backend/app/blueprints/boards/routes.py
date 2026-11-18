from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.boards import service
from app.blueprints.boards.schema import (
    BoardCreateSchema,
    BoardDetailSchema,
    BoardSummarySchema,
    BoardUpdateSchema,
)
from app.utils.responses import success_response

boards_bp = Blueprint("boards", __name__)


@boards_bp.post("/api/boards")
@jwt_required()
def create_board():
    payload = BoardCreateSchema().load(request.get_json(silent=True) or {})
    board = service.create_board(get_jwt_identity(), payload)
    return success_response(BoardSummarySchema().dump(board), 201)


@boards_bp.get("/api/boards")
@jwt_required()
def list_boards():
    boards = service.list_boards(get_jwt_identity())
    return success_response(BoardSummarySchema(many=True).dump(boards))


@boards_bp.get("/api/boards/<board_id>")
@jwt_required()
def get_board(board_id):
    board = service.get_board_detail(get_jwt_identity(), board_id)
    return success_response(BoardDetailSchema().dump(board))


@boards_bp.patch("/api/boards/<board_id>")
@jwt_required()
def update_board(board_id):
    payload = BoardUpdateSchema().load(request.get_json(silent=True) or {}, partial=True)
    board = service.update_board(get_jwt_identity(), board_id, payload)
    return success_response(BoardSummarySchema().dump(board))


@boards_bp.delete("/api/boards/<board_id>")
@jwt_required()
def delete_board(board_id):
    deleted_id = service.delete_board(get_jwt_identity(), board_id)
    return success_response({"id": deleted_id})

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.cards import service
from app.blueprints.cards.schema import (
    CardCreateSchema,
    CardDetailSchema,
    CardPositionSchema,
    CardSchema,
    CardUpdateSchema,
    TaskListSchema,
)
from app.utils.errors import ApiError
from app.utils.responses import success_response

cards_bp = Blueprint("cards", __name__)


@cards_bp.post("/api/columns/<column_id>/cards")
@jwt_required()
def create_card(column_id):
    payload = CardCreateSchema().load(request.get_json(silent=True) or {})
    card = service.create_card(get_jwt_identity(), column_id, payload)
    return success_response(CardSchema().dump(card), 201)


@cards_bp.get("/api/boards/<board_id>/cards")
@jwt_required()
def search_cards(board_id):
    cards = service.search_cards(get_jwt_identity(), board_id, request.args.get("q"))
    return success_response(CardSchema(many=True).dump(cards))


@cards_bp.get("/api/cards")
@jwt_required()
def my_tasks():
    if request.args.get("assignee") != "me":
        raise ApiError("Query parameter assignee must be 'me'", 400)
    data = service.list_my_tasks(get_jwt_identity())
    return success_response(TaskListSchema().dump(data))


@cards_bp.get("/api/cards/<card_id>")
@jwt_required()
def get_card(card_id):
    card = service.get_card_detail(get_jwt_identity(), card_id)
    return success_response(CardDetailSchema().dump(card))


@cards_bp.patch("/api/cards/<card_id>")
@jwt_required()
def update_card(card_id):
    payload = CardUpdateSchema().load(request.get_json(silent=True) or {}, partial=True)
    card = service.update_card(get_jwt_identity(), card_id, payload)
    return success_response(CardSchema().dump(card))


@cards_bp.patch("/api/cards/<card_id>/position")
@jwt_required()
def move_card(card_id):
    payload = CardPositionSchema().load(request.get_json(silent=True) or {})
    card, rebalanced = service.move_card(get_jwt_identity(), card_id, payload)
    data = CardSchema().dump(card)
    data["rebalanced"] = rebalanced
    return success_response(data)


@cards_bp.delete("/api/cards/<card_id>")
@jwt_required()
def delete_card(card_id):
    deleted_id = service.delete_card(get_jwt_identity(), card_id)
    return success_response({"id": deleted_id})

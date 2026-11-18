from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.columns import service
from app.blueprints.columns.schema import (
    ColumnCreateSchema,
    ColumnReorderSchema,
    ColumnSchema,
    ColumnUpdateSchema,
)
from app.utils.responses import success_response

columns_bp = Blueprint("columns", __name__)


@columns_bp.post("/api/boards/<board_id>/columns")
@jwt_required()
def create_column(board_id):
    payload = ColumnCreateSchema().load(request.get_json(silent=True) or {})
    column = service.create_column(get_jwt_identity(), board_id, payload)
    return success_response(ColumnSchema().dump(column), 201)


@columns_bp.patch("/api/boards/<board_id>/columns/reorder")
@jwt_required()
def reorder_column(board_id):
    payload = ColumnReorderSchema().load(request.get_json(silent=True) or {})
    column, rebalanced = service.reorder_column(get_jwt_identity(), board_id, payload)
    data = ColumnSchema().dump(column)
    data["rebalanced"] = rebalanced
    return success_response(data)


@columns_bp.patch("/api/columns/<column_id>")
@jwt_required()
def update_column(column_id):
    payload = ColumnUpdateSchema().load(request.get_json(silent=True) or {}, partial=True)
    column = service.update_column(get_jwt_identity(), column_id, payload)
    return success_response(ColumnSchema().dump(column))


@columns_bp.delete("/api/columns/<column_id>")
@jwt_required()
def delete_column(column_id):
    deleted_id = service.delete_column(get_jwt_identity(), column_id)
    return success_response({"id": deleted_id})

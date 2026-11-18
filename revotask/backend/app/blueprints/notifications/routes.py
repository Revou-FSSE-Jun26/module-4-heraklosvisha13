from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.notifications import service
from app.blueprints.notifications.schema import (
    NotificationItemSchema,
    NotificationPageSchema,
    PaginationSchema,
)
from app.utils.responses import success_response

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("/api/notifications")
@jwt_required()
def list_notifications():
    params = PaginationSchema().load(request.args.to_dict())
    data = service.list_notifications(get_jwt_identity(), params["page"], params["per_page"])
    return success_response(NotificationPageSchema().dump(data))


@notifications_bp.patch("/api/notifications/read-all")
@jwt_required()
def mark_all_read():
    return success_response({"updated": service.mark_all_read(get_jwt_identity())})


@notifications_bp.patch("/api/notifications/<notification_id>/read")
@jwt_required()
def mark_read(notification_id):
    notification = service.mark_read(get_jwt_identity(), notification_id)
    return success_response(NotificationItemSchema().dump(notification))

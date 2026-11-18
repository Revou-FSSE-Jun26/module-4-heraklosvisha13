from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.analytics import service
from app.blueprints.analytics.schema import AnalyticsSchema
from app.utils.responses import success_response

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/api/boards/<board_id>/analytics")
@jwt_required()
def get_analytics(board_id):
    data = service.get_analytics(get_jwt_identity(), board_id)
    return success_response(AnalyticsSchema().dump(data))

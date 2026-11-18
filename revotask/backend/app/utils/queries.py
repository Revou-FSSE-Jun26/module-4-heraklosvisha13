from app.utils.errors import ApiError


def get_active_or_404(model, item_id: str, label: str):
    item = model.active().filter_by(id=item_id).first()
    if item is None:
        raise ApiError(f"{label} not found", 404)
    return item

from sqlalchemy import func

from app.extensions import db

ORDER_STEP = 1000.0
MIN_GAP = 1e-6


def midpoint(prev_order: float | None, next_order: float | None) -> float:
    if prev_order is None and next_order is None:
        return ORDER_STEP
    if prev_order is None:
        return next_order / 2
    if next_order is None:
        return prev_order + ORDER_STEP
    return (prev_order + next_order) / 2


def next_order(model, scope_filter) -> float:
    """Order for a new last item: 1000.0 when the scope is empty, else max + 1000.0."""
    last = (
        db.session.query(func.max(model.order))
        .filter(scope_filter, model.deleted_at.is_(None))
        .scalar()
    )
    return ORDER_STEP if last is None else last + ORDER_STEP


def needs_rebalance(model, scope_filter, item_id: str, order: float) -> bool:
    """True when another active item in scope is closer than MIN_GAP (includes equality)."""
    return db.session.query(
        db.session.query(model.id)
        .filter(
            scope_filter,
            model.deleted_at.is_(None),
            model.id != item_id,
            func.abs(model.order - order) < MIN_GAP,
        )
        .exists()
    ).scalar()


def rebalance(model, scope_filter, moved_id: str) -> list[dict]:
    """Reassign 1000.0, 2000.0, ... inside the caller's transaction.

    Rows are locked with FOR UPDATE (limited to `model`'s table, because Card
    eager-loads outer-joined relationships). Nothing is committed here.
    """
    with db.session.begin_nested():
        items = (
            model.active()
            .filter(scope_filter)
            .order_by(model.order)
            .with_for_update(of=model)
            .all()
        )
        # exact ties: the moved item sorts after the item it collided with (D-13)
        items.sort(key=lambda i: (i.order, i.id == moved_id))
        for index, item in enumerate(items, start=1):
            item.order = index * ORDER_STEP
    return [{"id": i.id, "order": i.order} for i in items]

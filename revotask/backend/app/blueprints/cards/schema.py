from marshmallow import Schema, fields, pre_load, validate

from app.utils.schema import StrictSchema, order_field, uuid_str


class _CardFieldsMixin:
    @pre_load
    def strip_title(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("title"), str):
            data = {**data, "title": data["title"].strip()}
        return data


class CardCreateSchema(_CardFieldsMixin, StrictSchema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(allow_none=True)
    assignee_id = uuid_str(allow_none=True)
    due_date = fields.DateTime(allow_none=True)


class CardUpdateSchema(CardCreateSchema):
    """Loaded with partial=True; the service rejects an empty body."""


class CardPositionSchema(StrictSchema):
    column_id = uuid_str(required=True)
    order = order_field()


class CardSchema(Schema):
    id = fields.String()
    column_id = fields.String()
    board_id = fields.Function(lambda card: card.column.board_id)
    title = fields.String()
    description = fields.String(allow_none=True)
    assignee_id = fields.String(allow_none=True)
    assignee = fields.Function(
        lambda card: (
            {"id": card.assignee.id, "name": card.assignee.name} if card.assignee else None
        )
    )
    due_date = fields.DateTime(format="iso", allow_none=True)
    order = fields.Float()
    completed_at = fields.DateTime(format="iso", allow_none=True)
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")


class CommentSchema(Schema):
    id = fields.String()
    card_id = fields.String()
    author_id = fields.String()
    author_name = fields.Function(lambda c: c.author.name if c.author else None)
    body = fields.String()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")


class ActivitySchema(Schema):
    type = fields.String()
    actor_id = fields.String(allow_none=True)
    actor_name = fields.String(allow_none=True)
    created_at = fields.DateTime(format="iso")


class CardDetailSchema(CardSchema):
    comments = fields.List(fields.Nested(CommentSchema))
    activity = fields.List(fields.Nested(ActivitySchema))


class TaskItemSchema(Schema):
    id = fields.String()
    title = fields.String()
    board_id = fields.String()
    board_name = fields.String()
    column_name = fields.String()
    due_date = fields.DateTime(format="iso", allow_none=True)
    completed_at = fields.DateTime(format="iso", allow_none=True)


class TaskListSchema(Schema):
    items = fields.List(fields.Nested(TaskItemSchema))
    total = fields.Integer()
    completed = fields.Integer()
    open = fields.Integer()

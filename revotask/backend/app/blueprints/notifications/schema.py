from marshmallow import Schema, fields, validate

from app.utils.schema import StrictSchema


class PaginationSchema(StrictSchema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


class NotificationItemSchema(Schema):
    id = fields.String()
    type = fields.String()
    message = fields.String()
    board_id = fields.String()
    card_id = fields.String(allow_none=True)
    read_at = fields.DateTime(format="iso", allow_none=True)
    created_at = fields.DateTime(format="iso")


class NotificationPageSchema(Schema):
    items = fields.List(fields.Nested(NotificationItemSchema))
    page = fields.Integer()
    per_page = fields.Integer()
    total = fields.Integer()
    pages = fields.Integer()
    unread_count = fields.Integer()

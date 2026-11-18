from marshmallow import Schema, fields, pre_load, validate

from app.blueprints.cards.schema import CardSchema
from app.utils.schema import StrictSchema


def _strip_name(data):
    if isinstance(data, dict) and isinstance(data.get("name"), str):
        data = {**data, "name": data["name"].strip()}
    return data


class BoardCreateSchema(StrictSchema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))

    @pre_load
    def strip(self, data, **kwargs):
        return _strip_name(data)


class BoardUpdateSchema(BoardCreateSchema):
    """Loaded with partial=True; the service rejects an empty body."""


class BoardSummarySchema(Schema):
    id = fields.String()
    name = fields.String()
    role = fields.String()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")


class BoardColumnSchema(Schema):
    id = fields.String()
    board_id = fields.String()
    name = fields.String()
    order = fields.Float()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")
    cards = fields.List(fields.Nested(CardSchema))


class BoardDetailSchema(BoardSummarySchema):
    columns = fields.List(fields.Nested(BoardColumnSchema))

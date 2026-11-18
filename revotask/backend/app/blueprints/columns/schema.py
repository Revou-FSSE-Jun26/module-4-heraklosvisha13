from marshmallow import Schema, fields, pre_load, validate

from app.utils.schema import StrictSchema, order_field, uuid_str


class ColumnCreateSchema(StrictSchema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))

    @pre_load
    def strip(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            data = {**data, "name": data["name"].strip()}
        return data


class ColumnUpdateSchema(ColumnCreateSchema):
    """Loaded with partial=True; the service rejects an empty body."""


class ColumnReorderSchema(StrictSchema):
    column_id = uuid_str(required=True)
    order = order_field()


class ColumnSchema(Schema):
    id = fields.String()
    board_id = fields.String()
    name = fields.String()
    order = fields.Float()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")

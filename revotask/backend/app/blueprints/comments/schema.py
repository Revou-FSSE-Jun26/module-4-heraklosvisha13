from marshmallow import Schema, fields, pre_load, validate

from app.utils.schema import StrictSchema


class CommentBodySchema(StrictSchema):
    body = fields.String(required=True, validate=validate.Length(min=1, max=2000))

    @pre_load
    def strip_body(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("body"), str):
            data = {**data, "body": data["body"].strip()}
        return data


class CommentCreateSchema(CommentBodySchema):
    pass


class CommentUpdateSchema(CommentBodySchema):
    """Loaded with partial=True; the service rejects an empty body."""


class CommentSchema(Schema):
    id = fields.String()
    card_id = fields.String()
    author_id = fields.String()
    author_name = fields.Function(lambda c: c.author.name if c.author else None)
    body = fields.String()
    created_at = fields.DateTime(format="iso")
    updated_at = fields.DateTime(format="iso")

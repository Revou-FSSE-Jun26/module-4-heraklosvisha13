from marshmallow import RAISE, Schema, fields, validate

UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def uuid_str(**kwargs) -> fields.String:
    """String field that must be a UUID."""
    return fields.String(
        validate=validate.Regexp(UUID_REGEX, flags=2, error="Not a valid UUID."),  # re.I
        **kwargs,
    )


def order_field() -> fields.Float:
    return fields.Float(
        required=True,
        allow_nan=False,
        validate=validate.Range(min=0, min_inclusive=False),
    )


class StrictSchema(Schema):
    """Request schema that rejects unknown fields (D-05)."""

    class Meta:
        unknown = RAISE

from marshmallow import Schema, ValidationError, fields, post_load, pre_load, validate


class UserPublicSchema(Schema):
    id = fields.String()
    name = fields.String()
    email = fields.String()


class UserProfileSchema(UserPublicSchema):
    created_at = fields.DateTime(format="iso")


class UserUpdateSchema(Schema):
    """PATCH /api/users/me. Only `name` and `email`; `password` is rejected."""

    name = fields.String(validate=validate.Length(min=1, max=120))
    email = fields.Email(validate=validate.Length(max=255))

    @pre_load
    def reject_password(self, data, **kwargs):
        if isinstance(data, dict) and "password" in data:
            raise ValidationError(
                {"password": ["Password cannot be changed through this endpoint"]}
            )
        return data

    @post_load
    def normalize(self, data, **kwargs):
        if "name" in data:
            data["name"] = data["name"].strip()
            if not data["name"]:
                raise ValidationError({"name": ["Shorter than minimum length 1."]})
        if "email" in data:
            data["email"] = data["email"].strip().lower()
        if not data:
            raise ValidationError("At least one of name or email is required")
        return data

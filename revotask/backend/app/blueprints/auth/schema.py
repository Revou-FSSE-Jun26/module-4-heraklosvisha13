from marshmallow import Schema, fields, post_load, validate


class RegisterSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=8, max=128)
    )

    @post_load
    def normalize(self, data, **kwargs):
        data["name"] = data["name"].strip()
        data["email"] = data["email"].strip().lower()
        return data


class LoginSchema(Schema):
    email = fields.String(required=True, validate=validate.Length(min=1, max=255))
    password = fields.String(required=True, validate=validate.Length(min=1, max=128))

    @post_load
    def normalize(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        return data

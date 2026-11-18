from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from app.extensions import jwt
from app.utils.responses import error_response


class ApiError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message, self.status = message, status


def _flatten(messages, prefix=""):
    if isinstance(messages, dict):
        for key, value in messages.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten(value, path)
    elif isinstance(messages, (list, tuple)):
        plain = [m for m in messages if not isinstance(m, (dict, list))]
        if plain:
            yield prefix, plain
        for index, item in enumerate(messages):
            if isinstance(item, (dict, list)):
                yield from _flatten(item, f"{prefix}.{index}" if prefix else str(index))
    else:
        yield prefix, [messages]


def format_validation(messages) -> str:
    """{"email": ["Not a valid email address."]} -> "email: Not a valid email address."."""
    parts = []
    for field, errors in _flatten(messages):
        text = " ".join(map(str, errors))
        parts.append(f"{field}: {text}" if field and field != "_schema" else text)
    return "; ".join(parts)


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def api_error(e):
        return error_response(e.message, e.status)

    @app.errorhandler(ValidationError)
    def validation_error(e):
        return error_response(format_validation(e.messages), 400)

    @app.errorhandler(404)
    def not_found(e):
        return error_response("Not Found", 404)

    @app.errorhandler(HTTPException)
    def http_error(e):
        return error_response(e.name, e.code)

    @app.errorhandler(JWTExtendedException)
    def jwt_extended_error(e):
        return error_response("Invalid token", 401)

    @app.errorhandler(PyJWTError)
    def pyjwt_error(e):
        return error_response("Invalid token", 401)

    @app.errorhandler(Exception)
    def unexpected(e):
        app.logger.exception(e)
        return error_response("Internal server error", 500)

    @app.errorhandler(500)
    def server_error(e):
        return error_response("Internal server error", 500)

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response("Authentication required", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response("Invalid token", 401)

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return error_response("Token has expired", 401)

    @jwt.revoked_token_loader
    def revoked_token(header, payload):
        return error_response("Token has been revoked", 401)

    @jwt.needs_fresh_token_loader
    def needs_fresh(header, payload):
        return error_response("Fresh token required", 401)

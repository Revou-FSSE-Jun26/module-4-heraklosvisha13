import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

from app.extensions import cors, db, jwt, ma, migrate
from app.utils.errors import register_error_handlers
from app.utils.responses import success_response


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _load_config(app: Flask) -> None:
    app.config["SQLALCHEMY_DATABASE_URI"] = _require_env("DATABASE_URL").replace(
        "postgres://", "postgresql://", 1
    )
    app.config["JWT_SECRET_KEY"] = _require_env("JWT_SECRET_KEY")
    app.config["FRONTEND_URL"] = _require_env("FRONTEND_URL").rstrip("/")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
    )


def create_app(config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    if config is None:
        _load_config(app)
    else:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    cors.init_app(
        app, resources={r"/api/*": {"origins": app.config["FRONTEND_URL"]}}
    )

    from app import models  # noqa: F401  (register models for Alembic autodetect)

    register_error_handlers(app)

    from app.blueprints.analytics import analytics_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.boards import boards_bp
    from app.blueprints.cards import cards_bp
    from app.blueprints.columns import columns_bp
    from app.blueprints.comments import comments_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.users import users_bp
    for bp in (
        auth_bp, users_bp, boards_bp, columns_bp, cards_bp,
        comments_bp, notifications_bp, analytics_bp,
    ):
        app.register_blueprint(bp)


    @app.get("/api/health")
    def health():
        return success_response({"status": "ok"})

    return app

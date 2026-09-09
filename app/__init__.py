"""Flask application factory for AgriSmart AI."""

from flask import Flask, request
from flask_cors import CORS
from flask_login import LoginManager, current_user
from sqlalchemy import select

from app.errors import register_error_handlers
from app.models.database import db, initialize_database
from app.models.user import User
from app.routes import api_blueprint, auth_blueprint, main_blueprint
from app.services.model_loader import ModelLoader
from app.services.prediction_service import PredictionService
from app.utils.exceptions import ModelLoadError
from app.utils.logging_config import configure_logging
from app.utils.rate_limiter import configure_rate_limiter
from config import get_config


def create_app(environment: str | None = None) -> Flask:
    """Create, configure, and return the Flask application."""
    config_class = get_config(environment)
    app = Flask(
        __name__,
        static_folder=str(config_class.STATIC_DIR),
        template_folder=str(config_class.TEMPLATES_DIR),
    )
    app.config.from_object(config_class)

    _validate_production_config(app)
    configure_logging(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    initialize_database(app)
    _apply_configured_admin_roles(app)
    _initialize_login_manager(app)
    _initialize_prediction_service(app)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(api_blueprint)
    _register_chatbot_route_aliases(app)
    configure_rate_limiter(app)
    _configure_response_security(app)
    register_error_handlers(app)

    return app


def _register_chatbot_route_aliases(app: Flask) -> None:
    """Keep root chat API paths alongside the existing /api namespace."""
    aliases = (
        ("/chat", "api.chat", ["POST"]),
        ("/recommend", "api.chatbot_recommendation", ["POST"]),
        ("/weather", "api.weather_advice", ["GET"]),
        ("/crop-calendar", "api.crop_calendar", ["GET"]),
        ("/fertilizer", "api.fertilizer_advice", ["GET"]),
        ("/disease", "api.disease_advice", ["GET"]),
        ("/tips", "api.farming_tips", ["GET"]),
    )
    for path, view_name, methods in aliases:
        app.add_url_rule(path, endpoint=f"chatbot_{view_name}", view_func=app.view_functions[view_name], methods=methods)


def _initialize_login_manager(app: Flask) -> None:
    """Configure Flask-Login with the project User model."""
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        from flask import flash, jsonify, redirect, request, url_for
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "unauthorized",
                            "message": "Authentication is required to access this endpoint.",
                        },
                    }
                ),
                401,
            )
        flash("Please sign in to continue.", "info")
        return redirect(url_for("auth.login", next=request.path))

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        user = db.session.get(User, int(user_id)) if user_id.isdigit() else None
        if user is not None:
            app.logger.debug(
                "Loaded session user id=%s email=%s username=%s role=%s",
                user.id,
                user.email,
                user.display_username,
                user.role,
            )
        return user


def _apply_configured_admin_roles(app: Flask) -> None:
    """Promote only explicitly allowlisted account emails to the admin role."""
    admin_emails = app.config["ADMIN_EMAILS"]
    if not admin_emails:
        return
    with app.app_context():
        users = db.session.scalars(select(User).where(User.email.in_(admin_emails)))
        changed = False
        for user in users:
            if user.role != "admin":
                user.role = "admin"
                changed = True
        if changed:
            db.session.commit()
            app.logger.info("Configured administrator roles were applied.")


def _validate_production_config(app: Flask) -> None:
    """Prevent a production app from starting without a secret key."""
    if not app.config["DEBUG"] and not app.config["TESTING"]:
        if not app.config["SECRET_KEY"]:
            raise RuntimeError(
                "SECRET_KEY must be set before starting the production application."
            )


def _initialize_prediction_service(app: Flask) -> None:
    """Attempt one eager model load and store the reusable prediction service."""
    model_loader = ModelLoader(
        models_directory=app.config["MODEL_PATH"],
        processed_directory=app.config["PROCESSED_DATA_PATH"],
    )
    app.extensions["model_loader"] = model_loader
    app.extensions["prediction_service"] = PredictionService(model_loader)

    try:
        model_loader.load()
    except ModelLoadError as error:
        # The app stays available; future API integration returns a clean error.
        app.logger.error("Prediction model unavailable at startup: %s", error)


def _configure_response_security(app: Flask) -> None:
    """Log requests and add safe default headers to API responses."""

    @app.before_request
    def log_incoming_request() -> None:
        """Log only request metadata, never prediction input values."""
        app.logger.info("Incoming request: %s %s", request.method, request.path)

    @app.after_request
    def secure_response(response):
        """Apply safe browser headers and prevent API response caching."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(self), camera=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; "
            "frame-ancestors 'self'"
        )
        if request.path.startswith("/api/") or current_user.is_authenticated or request.path in {"/dashboard", "/predict", "/prediction", "/history", "/analytics", "/result", "/profile", "/model-info", "/model-upload"}:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

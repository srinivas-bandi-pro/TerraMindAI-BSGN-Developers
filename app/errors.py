"""HTTP error handlers for the Flask application."""

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    """Register application-wide error handlers."""

    @app.errorhandler(403)
    def forbidden(error: HTTPException):
        """Return an appropriate access-denied response for the request type."""
        app.logger.warning("Forbidden request: %s", request.path)
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "forbidden",
                            "message": "Administrator access is required.",
                        },
                    }
                ),
                403,
            )
        return render_template("access_denied.html"), 403

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        """Return consistent JSON responses for client and HTTP errors."""
        app.logger.warning("HTTP error %s: %s", error.code, error.description)
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": error.name.lower().replace(" ", "_"),
                        "message": error.description,
                    },
                }
            ),
            error.code,
        )

    @app.errorhandler(500)
    def internal_server_error(error: Exception):
        """Return a safe response for unexpected application errors."""
        app.logger.exception("Unhandled application error: %s", error)
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected server error occurred.",
                    },
                }
            ),
            500,
        )

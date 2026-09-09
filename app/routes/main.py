"""Top-level application and placeholder routes."""

from app.routes.api import health_status

from flask import Blueprint, current_app, redirect, render_template, url_for
from flask_login import login_required

from app.utils.decorators import admin_required


main_blueprint = Blueprint("main", __name__)

@main_blueprint.get("/")
def home():
    """Send every initial visit to the authentication landing page."""
    return redirect(url_for("auth.login"))


@main_blueprint.get("/favicon.ico")
def favicon():
    """Serve a clean inline SVG leaf favicon for browser requests."""
    from flask import Response
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🌱</text></svg>'
    return Response(svg, mimetype="image/svg+xml")



@main_blueprint.get("/health")
def health():
    """Return database and model health information."""
    return health_status()


@main_blueprint.get("/dashboard")
@login_required
def dashboard() -> str:
    """Render the analytics dashboard."""
    return render_template("dashboard.html")


@main_blueprint.get("/predict")
@login_required
def predict() -> str:
    """Render the crop prediction workspace."""
    return render_template("predict.html")


@main_blueprint.get("/prediction")
@login_required
def prediction() -> str:
    """Provide the requested prediction URL alongside the existing route."""
    return render_template("predict.html")


@main_blueprint.get("/analytics")
@login_required
def analytics() -> str:
    """Render the existing analytics dashboard workspace."""
    return render_template("dashboard.html")


@main_blueprint.get("/result")
@login_required
def result() -> str:
    """Render the latest crop prediction result view."""
    return render_template("result.html")


@main_blueprint.get("/model-info")
@admin_required
def model_info() -> str:
    """Render model information and frontend settings."""
    return render_template("model_info.html")


@main_blueprint.get("/model-upload")
@admin_required
def model_upload() -> str:
    """Render the local-only model artifact upload page."""
    return render_template(
        "model_upload.html",
        model_upload_enabled=current_app.config["MODEL_UPLOAD_ENABLED"],
    )


@main_blueprint.get("/history")
@login_required
def history() -> str:
    """Render the prediction history workspace."""
    return render_template("history.html")


@main_blueprint.get("/about")
def about() -> str:
    """Render the public project information page."""
    return render_template("about.html")


@main_blueprint.get("/contact")
def contact() -> str:
    """Render the frontend-only contact page."""
    return render_template("contact.html")

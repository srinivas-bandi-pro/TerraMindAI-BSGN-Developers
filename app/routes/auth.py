"""Authentication, account management, and profile routes."""

import logging
import os
import shutil
from urllib.parse import urljoin, urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.auth_service import AuthService, AuthenticationError


auth_blueprint = Blueprint("auth", __name__)
LOGGER = logging.getLogger(__name__)

# Ensure reference image is copied to static folder immediately
REF_IMAGE_SRC = r"C:\Users\bandi\.gemini\antigravity\brain\28084483-d022-46c8-8041-51dbd0191359\.user_uploaded\media_1788892009610.jpg"
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static"))
STATIC_BG_DEST = os.path.join(STATIC_DIR, "images", "ref_bg.jpg")

try:
    if os.path.exists(REF_IMAGE_SRC):
        os.makedirs(os.path.dirname(STATIC_BG_DEST), exist_ok=True)
        shutil.copy(REF_IMAGE_SRC, STATIC_BG_DEST)
except Exception as _err:
    LOGGER.warning("Could not copy reference background image on import: %s", _err)


@auth_blueprint.route("/bg-reference.jpg")
def bg_reference():
    """Serve the reference background image."""
    if os.path.exists(REF_IMAGE_SRC):
        return send_file(REF_IMAGE_SRC, mimetype="image/jpeg")
    if os.path.exists(STATIC_BG_DEST):
        return send_file(STATIC_BG_DEST, mimetype="image/jpeg")
    return "", 404






def _safe_next_url(target: str | None) -> str | None:
    """Allow redirects only to local application paths."""
    if not target:
        return None
    reference = urlparse(request.host_url)
    destination = urlparse(urljoin(request.host_url, target))
    return target if destination.scheme == reference.scheme and destination.netloc == reference.netloc else None


@auth_blueprint.route("/login", methods=("GET", "POST"))
def login():
    """Sign an existing user into a Flask-Login session."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("main.model_info"))
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identifier = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both your email/username and password.", "error")
            return render_template("login.html")

        user = AuthService.authenticate(identifier, password)
        if user is None:
            LOGGER.warning("Failed login attempt for identifier=%s", identifier)
            flash("Incorrect email address or password.", "error")
        else:
            remember_me = request.form.get("remember") == "on"
            login_user(user, remember=remember_me)
            LOGGER.info("Authenticated user id=%s email=%s username=%s role=%s", user.id, user.email, user.display_username, user.role)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = _safe_next_url(request.args.get("next"))
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("main.model_info"))
            return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@auth_blueprint.route("/register", methods=("GET", "POST"))
def register():
    """Create a standard user account and immediately sign it in."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")

        if not username and "@" in email:
            username = email.split("@", 1)[0].strip()

        clean_username_test = username.replace("_", "").replace(".", "").replace("-", "")

        if len(name) < 2:
            flash("Please enter your full name (at least 2 characters).", "error")
        elif not email or "@" not in email or len(email) > 255:
            flash("Please enter a valid email address.", "error")
        elif not username or not clean_username_test.isalnum():
            flash("Username may contain only letters, numbers, dots, hyphens, and underscores.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirmation:
            flash("Passwords do not match.", "error")
        else:
            try:
                role = "admin" if email in current_app.config["ADMIN_EMAILS"] else "user"
                user = AuthService.register(name, username, email, password, role=role)
            except AuthenticationError as error:
                flash(str(error), "error")
            else:
                login_user(user)
                LOGGER.debug("Registered user id=%s email=%s username=%s role=%s", user.id, user.email, user.display_username, user.role)
                flash("Your account has been created successfully. Welcome to TerraMind AI!", "success")
                return redirect(url_for("main.dashboard"))
    return render_template("register.html")


@auth_blueprint.route("/logout", methods=("GET", "POST"))
@login_required
def logout():
    """End the current authenticated browser session and clear state completely."""
    if current_user.is_authenticated:
        LOGGER.info("Logging out user id=%s email=%s", current_user.id, current_user.email)
    logout_user()
    from flask import session
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))


@auth_blueprint.get("/forgot-password")
def forgot_password():
    """Provide a safe placeholder until a mail-based reset flow is configured."""
    flash("Password reset will be available soon. Please contact your administrator.", "info")
    return redirect(url_for("auth.login"))


@auth_blueprint.get("/profile")
@login_required
def profile():
    """Render the current account profile."""
    return render_template("profile.html")


@auth_blueprint.route("/profile/change-password", methods=("GET", "POST"))
@login_required
def change_password():
    """Allow an authenticated user to change their own password."""
    if request.method == "POST":
        try:
            AuthService.change_password(current_user, request.form.get("current_password", ""), request.form.get("new_password", ""))
        except AuthenticationError as error:
            flash(str(error), "error")
        else:
            LOGGER.info("Password changed for user id=%s", current_user.id)
            flash("Your password has been updated.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("change_password.html")

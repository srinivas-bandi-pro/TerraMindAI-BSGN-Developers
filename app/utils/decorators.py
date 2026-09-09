"""Authorization decorators shared by protected application routes."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import abort
from flask_login import current_user, login_required


def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Require an authenticated administrator for model-management views."""

    @wraps(view)
    @login_required
    def wrapped_view(*args: Any, **kwargs: Any):
        if current_user.is_authenticated:
            from flask import current_app
            current_app.logger.debug("Admin check id=%s email=%s username=%s role=%s", current_user.id, current_user.email, current_user.display_username, current_user.role)
        if not current_user.is_admin:
            abort(403, description="Administrator access is required.")
        return view(*args, **kwargs)

    return wrapped_view

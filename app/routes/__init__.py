"""Route blueprints for AgriSmart AI."""

from app.routes.api import api_blueprint
from app.routes.auth import auth_blueprint
from app.routes.main import main_blueprint

__all__ = ["api_blueprint", "auth_blueprint", "main_blueprint"]

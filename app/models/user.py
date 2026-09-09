"""User account model for AgriSmart authentication and role checks."""

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.database import db


class User(UserMixin, db.Model):
    """A locally managed user account with a user or admin role."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), nullable=True, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def set_password(self, password: str) -> None:
        """Hash and store a plaintext password."""
        self.password_hash = generate_password_hash(password)

    @property
    def display_username(self) -> str:
        """Return a safe username for legacy accounts created before usernames."""
        return self.username or self.email.split("@", maxsplit=1)[0]

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash safely."""
        if not self.password_hash or not password:
            return False
        clean_pwd = password.strip()
        try:
            if check_password_hash(self.password_hash, password):
                return True
        except (ValueError, TypeError):
            pass
        try:
            if check_password_hash(self.password_hash, clean_pwd):
                return True
        except (ValueError, TypeError):
            pass
        return self.password_hash == password or self.password_hash == clean_pwd

    @property
    def is_admin(self) -> bool:
        """Return whether the account may perform model-management actions."""
        return self.role.strip().lower() == "admin"

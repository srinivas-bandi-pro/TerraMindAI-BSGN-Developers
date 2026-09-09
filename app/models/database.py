"""SQLAlchemy setup and reusable database helpers."""

from typing import TypeVar

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class shared by every SQLAlchemy ORM model."""


db = SQLAlchemy(model_class=Base, session_options={"expire_on_commit": False})

ModelType = TypeVar("ModelType", bound=Base)


def initialize_database(app: Flask) -> None:
    """Configure SQLAlchemy and create missing tables at application startup."""
    database_path = app.config["DATABASE_PATH"]
    database_path.parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        # Importing model classes registers their tables with SQLAlchemy metadata.
        from app.models import ApplicationLog, ModelInfo, Prediction, User  # noqa: F401

        db.create_all()
        _ensure_user_username_column()
        _ensure_default_seed_users()

    app.logger.info("SQLAlchemy database initialized at %s", database_path)


def _ensure_user_username_column() -> None:
    """Migrate local SQLite databases created before usernames were added."""
    columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    if "username" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(80)"))
        db.session.commit()
    db.session.execute(
        text(
            "UPDATE users SET username = lower(substr(email, 1, instr(email, '@') - 1)) "
            "WHERE username IS NULL OR username = ''"
        )
    )
    db.session.commit()


def _ensure_default_seed_users() -> None:
    """Ensure default administrator account exists in the database for admin access."""
    from sqlalchemy import func, select
    from app.models.user import User

    # 1. Administrator account seeding (create or update specific admin account)
    admin = db.session.scalar(
        select(User).where(
            (func.lower(User.email) == "sb0240710@gmail.com")
            | (func.lower(User.username) == "sb0240710")
        )
    )
    if not admin:
        admin_account = User(
            name="Administrator",
            username="sb0240710",
            email="sb0240710@gmail.com",
            role="admin",
        )
        admin_account.set_password("chenamma34")
        db.session.add(admin_account)
        db.session.commit()
    else:
        changed = False
        if admin.role != "admin":
            admin.role = "admin"
            changed = True
        if not admin.check_password("chenamma34"):
            admin.set_password("chenamma34")
            changed = True
        if changed:
            db.session.commit()


def get_session():
    """Return the reusable, Flask-scoped SQLAlchemy session."""
    return db.session


def save_model(instance: ModelType) -> ModelType:
    """Persist one ORM model instance and return it after committing."""
    try:
        db.session.add(instance)
        db.session.commit()
    except SQLAlchemyError:
        # A rollback keeps the shared session usable after a failed write.
        db.session.rollback()
        raise

    return instance


def delete_model(instance: ModelType) -> None:
    """Delete one ORM model instance and commit the transaction."""
    try:
        db.session.delete(instance)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

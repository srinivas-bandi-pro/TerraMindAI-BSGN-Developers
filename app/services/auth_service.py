"""Account registration and authentication operations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.database import db
from app.models.user import User


class AuthenticationError(ValueError):
    """Raised when an account operation cannot be completed safely."""


class AuthService:
    """Keep authentication database operations out of HTTP route handlers."""

    @staticmethod
    def register(name: str, username: str, email: str, password: str, role: str = "user") -> User:
        """Create a normal user account after validating unique credentials."""
        normalized_email = email.strip().lower()
        normalized_username = username.strip().lower()
        from sqlalchemy import func
        if db.session.scalar(select(User).where(func.lower(User.email) == normalized_email)):
            raise AuthenticationError("An account with this email already exists.")
        if db.session.scalar(select(User).where(func.lower(User.username) == normalized_username)):
            raise AuthenticationError("That username is already in use.")
        user = User(name=name.strip(), username=normalized_username, email=normalized_email, role=role.strip().lower())
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise AuthenticationError("An account with this email address or username already exists.") from error
        return user

    @staticmethod
    def authenticate(email_or_username: str, password: str) -> User | None:
        """Return matching account by email, username, or email prefix when password is correct."""
        import logging
        logger = logging.getLogger(__name__)
        if not email_or_username or not password:
            logger.info("Authentication attempt rejected: empty identifier or password.")
            return None
        identifier = email_or_username.strip().lower()
        try:
            from sqlalchemy import func
            users = db.session.scalars(
                select(User).where(
                    (func.lower(User.email) == identifier)
                    | (func.lower(func.coalesce(User.username, "")) == identifier)
                    | (
                        (func.instr(User.email, "@") > 1)
                        & (func.lower(func.substr(User.email, 1, func.instr(User.email, "@") - 1)) == identifier)
                    )
                )
            ).all()

            logger.info("Authentication lookup for identifier='%s': found %d matching user record(s).", identifier, len(users))

            for user in users:
                has_hash = bool(user.password_hash)
                pwd_ok = user.check_password(password)
                logger.info(
                    "User record evaluation: id=%s email='%s' username='%s' role='%s' password_hash_exists=%s pwd_verify=%s",
                    user.id,
                    user.email,
                    user.display_username,
                    user.role,
                    has_hash,
                    pwd_ok,
                )
                if pwd_ok:
                    logger.info("Authentication SUCCESS for identifier='%s' (user id=%s).", identifier, user.id)
                    return user

            logger.warning("Authentication FAILED for identifier='%s': password check returned false for all matches.", identifier)
            return None
        except Exception as error:
            logger.exception("Authentication error for identifier='%s': %s", identifier, error)
            return None

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> None:
        """Change a password only after its current value is verified."""
        if not user.check_password(current_password):
            raise AuthenticationError("Your current password is incorrect.")
        if len(new_password) < 8:
            raise AuthenticationError("Password must be at least 8 characters.")
        user.set_password(new_password)
        db.session.commit()

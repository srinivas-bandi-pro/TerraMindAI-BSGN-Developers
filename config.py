"""Environment-specific configuration for AgriSmart AI."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv_file(env_path: Path) -> None:
    """Load KEY=VALUE environment pairs from a local .env file when present."""
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv_file(BASE_DIR / ".env")


def sqlite_uri(database_path: Path) -> str:
    """Build a SQLite SQLAlchemy connection URI from a file path."""
    return f"sqlite:///{database_path.as_posix()}"


def resolve_database_config() -> tuple[Path, str]:
    """Resolve database file path and SQLAlchemy URI to absolute paths."""
    env_url = os.environ.get("DATABASE_URL")
    env_path = os.environ.get("DATABASE_PATH")

    if env_url:
        if env_url.startswith("sqlite:///"):
            raw_path = env_url[10:]
            if raw_path == ":memory:":
                return Path(":memory:"), "sqlite:///:memory:"
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                db_path = (BASE_DIR / db_path).resolve()
            else:
                db_path = db_path.resolve()
            return db_path, sqlite_uri(db_path)
        return Path(env_path or BASE_DIR / "database" / "agrismart.db"), env_url

    if env_path:
        db_path = Path(env_path)
        if not db_path.is_absolute():
            db_path = (BASE_DIR / db_path).resolve()
        else:
            db_path = db_path.resolve()
    else:
        db_path = (BASE_DIR / "database" / "agrismart.db").resolve()

    return db_path, sqlite_uri(db_path)


_DEFAULT_DB_PATH, _DEFAULT_DB_URI = resolve_database_config()


class BaseConfig:
    """Settings shared by every application environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE_PATH = _DEFAULT_DB_PATH
    SQLALCHEMY_DATABASE_URI = _DEFAULT_DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_DIR = BASE_DIR / "templates"
    STATIC_DIR = BASE_DIR / "static"
    MODEL_PATH = Path(os.environ.get("MODEL_PATH", BASE_DIR / "models"))
    PROCESSED_DATA_PATH = Path(
        os.environ.get("PROCESSED_DATA_PATH", BASE_DIR / "data" / "processed")
    )
    LOG_DIR = Path(os.environ.get("LOG_DIR", BASE_DIR / "logs"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "true").lower() == "true"
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))
    HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", os.environ.get("FLASK_PORT", "5000")))
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW_SECONDS = int(
        os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60")
    )
    MAX_CONTENT_LENGTH = int(
        os.environ.get("MAX_CONTENT_LENGTH", str(200 * 1024 * 1024))
    )
    MODEL_UPLOAD_ENABLED = False
    ADMIN_EMAILS = {
        email.strip().lower()
        for email in os.environ.get(
            "ADMIN_EMAILS", "sb0240710@gmail.com,admin@terramind.ai,admin@agrismart.ai"
        ).split(",")
        if email.strip()
    }
    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    """Configuration used during local development."""

    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-secret-key")
    MODEL_UPLOAD_ENABLED = True


class TestingConfig(BaseConfig):
    """Configuration reserved for automated tests."""

    TESTING = True
    SECRET_KEY = "testing-only-secret-key"
    DATABASE_PATH = BASE_DIR / "database" / "test_agrismart.db"
    SQLALCHEMY_DATABASE_URI = sqlite_uri(DATABASE_PATH)


class ProductionConfig(BaseConfig):
    """Configuration used by a production WSGI server."""


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(environment: str | None = None) -> type[BaseConfig]:
    """Return the configuration class for the requested environment."""
    selected_environment = (environment or os.environ.get(
        "FLASK_ENV", "development"
    )).lower()

    return CONFIG_BY_NAME.get(selected_environment, ProductionConfig)

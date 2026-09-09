"""Production-safe logging configuration for the Flask application."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask
from flask.logging import default_handler


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def _has_named_handler(logger: logging.Logger, name: str) -> bool:
    """Return whether a handler installed by this application already exists."""
    return any(handler.name == name for handler in logger.handlers)


def _rotating_handler(
    path: Path,
    level: int,
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    """Build a delayed rotating file handler with the shared format."""
    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def configure_logging(app: Flask) -> None:
    """Configure console, application, and error logs without duplicate handlers."""
    log_level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)
    log_directory = Path(app.config["LOG_DIR"])
    log_directory.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()

    if default_handler in app.logger.handlers:
        app.logger.removeHandler(default_handler)

    app.logger.setLevel(log_level)
    app.logger.propagate = True
    root_logger.setLevel(log_level)

    if not _has_named_handler(root_logger, "agrismart-console"):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.name = "agrismart-console"
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(console_handler)

    if not app.config["LOG_TO_FILE"]:
        return

    max_bytes = app.config["LOG_MAX_BYTES"]
    backup_count = app.config["LOG_BACKUP_COUNT"]
    if not _has_named_handler(root_logger, "agrismart-application-file"):
        application_handler = _rotating_handler(
            log_directory / "application.log",
            log_level,
            max_bytes,
            backup_count,
        )
        application_handler.name = "agrismart-application-file"
        root_logger.addHandler(application_handler)

    if not _has_named_handler(root_logger, "agrismart-error-file"):
        error_handler = _rotating_handler(
            log_directory / "error.log",
            logging.ERROR,
            max_bytes,
            backup_count,
        )
        error_handler.name = "agrismart-error-file"
        root_logger.addHandler(error_handler)

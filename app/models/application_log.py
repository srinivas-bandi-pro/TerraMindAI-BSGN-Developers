"""Application log database model."""

from datetime import datetime

from app.models.database import db


class ApplicationLog(db.Model):
    """Store important application events for later review."""

    __tablename__ = "application_logs"

    id = db.Column(db.Integer, primary_key=True)
    log_level = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return a concise representation useful during debugging."""
        return f"<ApplicationLog id={self.id} level={self.log_level!r}>"

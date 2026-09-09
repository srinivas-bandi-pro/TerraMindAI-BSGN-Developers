"""Prediction database model."""

from datetime import datetime

from app.models.database import db


class Prediction(db.Model):
    """Store one crop recommendation request and its result."""

    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    predicted_crop = db.Column(db.String(100), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return a concise representation useful during debugging."""
        return f"<Prediction id={self.id} crop={self.predicted_crop!r}>"

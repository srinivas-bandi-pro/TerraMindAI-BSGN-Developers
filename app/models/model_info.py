"""Machine-learning model metadata database model."""

from datetime import datetime

from app.models.database import db


class ModelInfo(db.Model):
    """Store metadata about a trained machine-learning model version."""

    __tablename__ = "model_info"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(120), nullable=False)
    algorithm = db.Column(db.String(120), nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    version = db.Column(db.String(50), nullable=False, unique=True)
    trained_on = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    feature_count = db.Column(db.Integer, nullable=False)
    dataset_name = db.Column(db.String(255), nullable=False)

    def __repr__(self) -> str:
        """Return a concise representation useful during debugging."""
        return f"<ModelInfo id={self.id} version={self.version!r}>"

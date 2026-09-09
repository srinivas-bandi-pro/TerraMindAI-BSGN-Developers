"""Database persistence and retrieval for prediction history."""

import logging
from datetime import datetime

from sqlalchemy import func

from sqlalchemy.exc import SQLAlchemyError

from app.models.database import db
from app.models.prediction import Prediction
from app.services.input_validator import PredictionInput
from app.utils.exceptions import PredictionPersistenceError


LOGGER = logging.getLogger(__name__)


class PredictionHistoryService:
    """Save successful predictions and provide recent prediction history."""

    def save_prediction(
        self,
        prediction_input: PredictionInput,
        predicted_crop: str,
        confidence_score: float,
    ) -> Prediction:
        """Store a successful recommendation in the SQLite prediction table."""
        history_record = Prediction(
            nitrogen=prediction_input.nitrogen,
            phosphorus=prediction_input.phosphorus,
            potassium=prediction_input.potassium,
            temperature=prediction_input.temperature,
            humidity=prediction_input.humidity,
            ph=prediction_input.ph,
            rainfall=prediction_input.rainfall,
            predicted_crop=predicted_crop,
            confidence_score=confidence_score,
        )

        try:
            db.session.add(history_record)
            db.session.commit()
            LOGGER.info("Saved prediction history record %s.", history_record.id)
            return history_record
        except SQLAlchemyError as error:
            db.session.rollback()
            LOGGER.exception("Unable to save prediction history.")
            raise PredictionPersistenceError(
                "Prediction could not be saved. Please try again later."
            ) from error

    def get_recent_predictions(self, limit: int = 20) -> list[Prediction]:
        """Return recent predictions with a bounded, safe limit."""
        safe_limit = max(1, min(limit, 100))
        return (
            Prediction.query.order_by(Prediction.created_at.desc())
            .limit(safe_limit)
            .all()
        )

    def get_paginated_predictions(
        self,
        page: int,
        per_page: int,
    ) -> tuple[list[Prediction], int]:
        """Return newest-first prediction history and its total record count."""
        query = Prediction.query.order_by(Prediction.created_at.desc())
        total_records = query.count()
        records = query.offset((page - 1) * per_page).limit(per_page).all()
        return records, total_records

    def delete_prediction(self, prediction_id: int) -> bool:
        """Delete one prediction by ID and return whether it existed."""
        history_record = db.session.get(Prediction, prediction_id)
        if history_record is None:
            return False

        try:
            db.session.delete(history_record)
            db.session.commit()
            LOGGER.info("Deleted prediction history record %s.", prediction_id)
            return True
        except SQLAlchemyError as error:
            db.session.rollback()
            LOGGER.exception("Unable to delete prediction history record.")
            raise PredictionPersistenceError(
                "Prediction history could not be deleted. Please try again later."
            ) from error

    def dashboard_summary(self, recent_limit: int = 5) -> dict[str, object]:
        """Return aggregated data used by the backend dashboard endpoint."""
        total_predictions = Prediction.query.count()
        most_predicted = (
            db.session.query(
                Prediction.predicted_crop,
                func.count(Prediction.id).label("crop_count"),
            )
            .group_by(Prediction.predicted_crop)
            .order_by(func.count(Prediction.id).desc())
            .first()
        )
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        predictions_today = Prediction.query.filter(
            Prediction.created_at >= today_start
        ).count()

        return {
            "total_predictions": total_predictions,
            "most_predicted_crop": most_predicted[0] if most_predicted else None,
            "predictions_today": predictions_today,
            "recent_predictions": self.get_recent_predictions(recent_limit),
        }

    def statistics_summary(self) -> dict[str, object]:
        """Return crop distribution and confidence aggregates for the API."""
        crop_distribution = (
            db.session.query(
                Prediction.predicted_crop,
                func.count(Prediction.id).label("prediction_count"),
            )
            .group_by(Prediction.predicted_crop)
            .order_by(Prediction.predicted_crop.asc())
            .all()
        )
        average_confidence = db.session.query(
            func.avg(Prediction.confidence_score)
        ).scalar()

        return {
            "crop_distribution": {
                crop: count for crop, count in crop_distribution
            },
            "average_confidence": float(average_confidence or 0),
            "prediction_count": Prediction.query.count(),
        }

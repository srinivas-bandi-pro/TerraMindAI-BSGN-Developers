"""Production-style crop recommendation prediction orchestration."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

import numpy as np
import pandas as pd

from app.services.history_service import PredictionHistoryService
from app.services.input_validator import PredictionInput, validate_prediction_input
from app.services.model_loader import ModelArtifacts, ModelLoader
from app.utils.exceptions import (
    InputValidationError,
    ModelUnavailableError,
    PredictionPersistenceError,
)


LOGGER = logging.getLogger(__name__)
FEATURE_ORDER = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
]


@dataclass(frozen=True)
class CropRecommendation:
    """Structured successful prediction response returned by the service."""

    predicted_crop: str
    confidence: float
    prediction_probability: float
    alternative_crops: list[dict[str, float | str]]
    prediction_timestamp: str
    model_version: str
    algorithm_name: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the recommendation to a JSON-ready dictionary."""
        return {
            "predicted_crop": self.predicted_crop,
            "confidence": self.confidence,
            "prediction_probability": self.prediction_probability,
            "alternative_crops": self.alternative_crops,
            "prediction_timestamp": self.prediction_timestamp,
            "model_version": self.model_version,
            "algorithm_name": self.algorithm_name,
        }


class PredictionService:
    """Validate, preprocess, predict, and persist crop recommendations."""

    def __init__(
        self,
        model_loader: ModelLoader,
        history_service: PredictionHistoryService | None = None,
    ) -> None:
        self.model_loader = model_loader
        self.history_service = history_service or PredictionHistoryService()

    def predict(self, payload: Mapping[str, Any]) -> CropRecommendation:
        """Return a persisted crop recommendation or raise a domain exception."""
        try:
            prediction_input = validate_prediction_input(payload)
        except InputValidationError:
            LOGGER.warning("Prediction validation failed.")
            raise

        artifacts = self.model_loader.get_artifacts()
        raw_values = prediction_input.as_feature_list()
        features = pd.DataFrame(
            [raw_values],
            columns=FEATURE_ORDER,
        )
        scaled_features = artifacts.scaler.transform(features)
        encoded_prediction = int(artifacts.model.predict(scaled_features)[0])
        probabilities, classes = self._prediction_probabilities(
            artifacts,
            scaled_features,
        )
        recommended_crop = self._decode_crop(artifacts, encoded_prediction)
        top_recommendations = self._top_recommendations(
            artifacts,
            probabilities,
            classes,
        )
        confidence = self._confidence_for_prediction(
            encoded_prediction,
            probabilities,
            classes,
        )
        top_indices = np.argsort(probabilities)[::-1][:5]
        top_probabilities = [
            {
                "crop": self._decode_crop(artifacts, int(classes[index])),
                "probability": round(float(probabilities[index]), 6),
            }
            for index in top_indices
        ]
        LOGGER.debug(
            "Prediction trace: feature_order=%s raw=%s scaled=%s model_class=%s "
            "raw_prediction=%s decoded_prediction=%s confidence=%.6f top5=%s",
            FEATURE_ORDER,
            raw_values,
            np.asarray(scaled_features).tolist(),
            type(artifacts.model).__name__,
            encoded_prediction,
            recommended_crop,
            confidence,
            top_probabilities,
        )

        self.history_service.save_prediction(
            prediction_input,
            recommended_crop,
            confidence,
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        LOGGER.info(
            "Prediction completed successfully: crop=%s confidence=%.4f.",
            recommended_crop,
            confidence,
        )
        return CropRecommendation(
            predicted_crop=recommended_crop,
            confidence=confidence,
            prediction_probability=confidence,
            alternative_crops=top_recommendations,
            prediction_timestamp=timestamp,
            model_version=str(
                artifacts.metadata.get(
                    "model_version",
                    artifacts.metadata.get(
                        "version",
                        artifacts.metadata.get("dataset_version", "unknown"),
                    ),
                )
            ),
            algorithm_name=str(artifacts.metadata.get("algorithm", "unknown")),
        )

    def predict_safe(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Return structured success or clean error data for an API layer."""
        try:
            recommendation = self.predict(payload)
            return {"success": True, "data": recommendation.to_dict()}
        except InputValidationError as error:
            return {
                "success": False,
                "error": {"code": "validation_error", "fields": error.errors},
            }
        except ModelUnavailableError as error:
            LOGGER.error("Prediction requested while model is unavailable.")
            return {
                "success": False,
                "error": {"code": "model_unavailable", "message": str(error)},
            }
        except PredictionPersistenceError as error:
            return {
                "success": False,
                "error": {"code": "database_error", "message": str(error)},
            }
        except Exception:
            LOGGER.exception("Unexpected prediction service error.")
            return {
                "success": False,
                "error": {
                    "code": "prediction_error",
                    "message": "An unexpected error occurred during prediction.",
                },
            }

    @staticmethod
    def _decode_crop(artifacts: ModelArtifacts, encoded_crop: int) -> str:
        """Decode the model's encoded crop class into its original label."""
        return str(artifacts.label_encoder.inverse_transform([encoded_crop])[0])

    @staticmethod
    def _prediction_probabilities(
        artifacts: ModelArtifacts,
        scaled_features: Any,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return class probabilities from native probabilities or model scores."""
        model = artifacts.model
        classes = np.asarray(model.classes_)

        if hasattr(model, "predict_proba"):
            return np.asarray(model.predict_proba(scaled_features)[0]), classes

        if hasattr(model, "decision_function"):
            scores = np.asarray(model.decision_function(scaled_features))
            if scores.ndim == 1:
                scores = np.column_stack((-scores, scores))
            scores = scores[0]
            normalized_scores = scores - np.max(scores)
            probabilities = np.exp(normalized_scores)
            return probabilities / probabilities.sum(), classes

        raise ModelUnavailableError(
            "Loaded model cannot provide confidence scores for predictions."
        )

    def _top_recommendations(
        self,
        artifacts: ModelArtifacts,
        probabilities: np.ndarray,
        classes: np.ndarray,
    ) -> list[dict[str, float | str]]:
        """Return the top three decoded crops ordered by prediction probability."""
        top_indices = np.argsort(probabilities)[::-1][:3]
        recommendations = []

        for index in top_indices:
            crop = self._decode_crop(artifacts, int(classes[index]))
            recommendations.append(
                {"crop": crop, "confidence": round(float(probabilities[index]), 4)}
            )

        return recommendations

    @staticmethod
    def _confidence_for_prediction(
        encoded_prediction: int,
        probabilities: np.ndarray,
        classes: np.ndarray,
    ) -> float:
        """Return the probability associated with the predicted crop class."""
        matching_index = np.where(classes == encoded_prediction)[0]
        if matching_index.size == 0:
            return round(float(np.max(probabilities)), 4)
        return round(float(probabilities[matching_index[0]]), 4)

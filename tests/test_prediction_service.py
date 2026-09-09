"""Unit tests for prediction-service validation and response behaviour."""

import unittest

import numpy as np

from app.services.model_loader import ModelArtifacts
from app.services.prediction_service import PredictionService


class FakeModel:
    """Small deterministic classifier substitute for prediction-service tests."""

    classes_ = np.array([0, 1, 2])

    def predict(self, features: object) -> np.ndarray:
        """Return a fixed encoded crop label."""
        return np.array([0])

    def predict_proba(self, features: object) -> np.ndarray:
        """Return stable probabilities for three crop labels."""
        return np.array([[0.80, 0.15, 0.05]])


class FakeScaler:
    """Identity scaler used to isolate service logic in tests."""

    def transform(self, features: object) -> object:
        """Return unchanged features."""
        return features


class FakeLabelEncoder:
    """Decode test crop classes into readable crop names."""

    labels = np.array(["rice", "maize", "chickpea"])

    def inverse_transform(self, labels: object) -> np.ndarray:
        """Decode integer labels used by the fake model."""
        return self.labels[np.asarray(labels, dtype=int)]


class FakeModelLoader:
    """Return prepared artifacts without accessing the filesystem."""

    def __init__(self, artifacts: ModelArtifacts | None = None) -> None:
        self.artifacts = artifacts

    def get_artifacts(self) -> ModelArtifacts:
        """Return test artifacts or simulate an unavailable model."""
        if self.artifacts is None:
            from app.utils.exceptions import ModelUnavailableError

            raise ModelUnavailableError("Prediction model is unavailable.")
        return self.artifacts


class FakeHistoryService:
    """Record save calls without requiring a Flask database context."""

    def __init__(self) -> None:
        self.saved = False

    def save_prediction(self, *args: object) -> None:
        """Mark a successful history save."""
        self.saved = True


class PredictionServiceTests(unittest.TestCase):
    """Verify normal and error behaviour of the prediction service."""

    def setUp(self) -> None:
        """Build a service with deterministic inference dependencies."""
        artifacts = ModelArtifacts(
            model=FakeModel(),
            label_encoder=FakeLabelEncoder(),
            scaler=FakeScaler(),
            metadata={"algorithm": "Random Forest", "model_version": "1.0"},
        )
        self.history_service = FakeHistoryService()
        self.service = PredictionService(
            FakeModelLoader(artifacts),
            self.history_service,
        )
        self.valid_payload = {
            "nitrogen": 90,
            "phosphorus": 42,
            "potassium": 43,
            "temperature": 21.5,
            "humidity": 82,
            "ph": 6.5,
            "rainfall": 200,
        }

    def test_valid_prediction(self) -> None:
        """A valid request returns a decoded crop and saves history."""
        response = self.service.predict_safe(self.valid_payload)

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["predicted_crop"], "rice")
        self.assertEqual(response["data"]["confidence"], 0.8)
        self.assertTrue(self.history_service.saved)

    def test_missing_fields(self) -> None:
        """A missing required field returns field-level validation errors."""
        payload = self.valid_payload.copy()
        payload.pop("rainfall")

        response = self.service.predict_safe(payload)

        self.assertFalse(response["success"])
        self.assertIn("rainfall", response["error"]["fields"])

    def test_invalid_numbers(self) -> None:
        """A non-numeric value is rejected before model inference."""
        payload = self.valid_payload.copy()
        payload["nitrogen"] = "not-a-number"

        response = self.service.predict_safe(payload)

        self.assertFalse(response["success"])
        self.assertIn("nitrogen", response["error"]["fields"])

    def test_out_of_range_values(self) -> None:
        """A physically impossible humidity value is rejected."""
        payload = self.valid_payload.copy()
        payload["humidity"] = 101

        response = self.service.predict_safe(payload)

        self.assertFalse(response["success"])
        self.assertIn("humidity", response["error"]["fields"])

    def test_negative_and_extreme_values(self) -> None:
        """Negative and impractically large values are rejected before inference."""
        payload = self.valid_payload.copy()
        payload["nitrogen"] = -1
        payload["rainfall"] = 5000

        response = self.service.predict_safe(payload)

        self.assertFalse(response["success"])
        self.assertIn("nitrogen", response["error"]["fields"])
        self.assertIn("rainfall", response["error"]["fields"])

    def test_model_unavailable(self) -> None:
        """An unavailable model produces a clean structured response."""
        unavailable_service = PredictionService(
            FakeModelLoader(),
            FakeHistoryService(),
        )

        response = unavailable_service.predict_safe(self.valid_payload)

        self.assertFalse(response["success"])
        self.assertEqual(response["error"]["code"], "model_unavailable")

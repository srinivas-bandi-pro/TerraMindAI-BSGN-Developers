"""Endpoint tests for the AgriSmart AI backend API."""

import unittest
from types import SimpleNamespace

from app import create_app
from app.models.database import db
from app.models.prediction import Prediction
from app.models.user import User


class FakeModelLoader:
    """Provide deterministic metadata without loading filesystem artifacts."""

    def get_artifacts(self) -> SimpleNamespace:
        """Return metadata expected by health and model API endpoints."""
        return SimpleNamespace(
            metadata={
                "algorithm": "Random Forest",
                "accuracy": 0.98,
                "model_version": "1.0",
                "training_date": "2026-01-01T00:00:00+00:00",
                "dataset_name": "processed_dataset.csv",
                "feature_count": 7,
            }
        )


class FakePredictionService:
    """Return stable prediction results without invoking a trained model."""

    def predict_safe(self, payload: dict) -> dict:
        """Return success for valid test payloads and validation errors otherwise."""
        if "N" not in payload:
            return {
                "success": False,
                "error": {
                    "code": "validation_error",
                    "fields": {"nitrogen": "This field is required."},
                },
            }

        return {
            "success": True,
            "data": {
                "predicted_crop": "rice",
                "confidence": 0.9873,
                "prediction_probability": 0.9873,
                "alternative_crops": [
                    {"crop": "rice", "confidence": 0.9873},
                    {"crop": "maize", "confidence": 0.01},
                    {"crop": "chickpea", "confidence": 0.0027},
                ],
                "prediction_timestamp": "2026-01-01T00:00:00+00:00",
                "model_version": "1.0",
                "algorithm_name": "Random Forest",
            },
        }


class ApiTests(unittest.TestCase):
    """Verify public API responses, validation, history, and statistics."""

    def setUp(self) -> None:
        """Create an isolated testing app and seed one history record."""
        self.app = create_app("testing")
        self.app.extensions["model_loader"] = FakeModelLoader()
        self.app.extensions["prediction_service"] = FakePredictionService()
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(
                Prediction(
                    nitrogen=90,
                    phosphorus=42,
                    potassium=43,
                    temperature=20.8,
                    humidity=82,
                    ph=6.5,
                    rainfall=202,
                    predicted_crop="rice",
                    confidence_score=0.9873,
                )
            )
            self.user = User(
                name="API Test User",
                email="api-test@example.com",
                role="user",
            )
            self.user.set_password("test-password")
            db.session.add(self.user)
            db.session.commit()
        self._sign_in()

    def tearDown(self) -> None:
        """Remove database records after each endpoint test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _sign_in(self) -> None:
        """Create a standard Flask-Login session for protected endpoints."""
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.user.id)
            session["_fresh"] = True

    def test_home_page(self) -> None:
        """The root endpoint always sends visitors to the login landing page."""
        anonymous_client = self.app.test_client()
        response = anonymous_client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_public_pages_render(self) -> None:
        """Public application pages return usable HTML responses."""
        for path in ("/about", "/contact", "/predict", "/dashboard", "/history"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("main-content", response.get_data(as_text=True))

    def test_health_endpoint(self) -> None:
        """Health reports available database and model components."""
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["model_status"], "loaded")

    def test_model_endpoint(self) -> None:
        """Model endpoint returns the loaded metadata payload."""
        response = self.client.get("/api/model")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["algorithm"], "Random Forest")

    def test_prediction_endpoint(self) -> None:
        """Valid prediction JSON returns the required API response fields."""
        response = self.client.post(
            "/api/predict",
            json={
                "N": 90,
                "P": 42,
                "K": 43,
                "temperature": 20.8,
                "humidity": 82,
                "ph": 6.5,
                "rainfall": 202,
            },
        )

        response_data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["prediction"], "rice")
        self.assertEqual(response_data["confidence"], 98.73)

    def test_prediction_validation_error(self) -> None:
        """Invalid prediction input receives a 422 JSON error response."""
        response = self.client.post("/api/predict", json={"temperature": 20})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["error"]["code"], "validation_error")

    def test_prediction_rejects_non_json_payload(self) -> None:
        """Prediction requests must contain a JSON object."""
        response = self.client.post("/api/predict", data="not-json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_json")

    def test_invalid_pagination_and_missing_history_record(self) -> None:
        """History endpoints return structured errors for invalid requests."""
        pagination_response = self.client.get("/api/history?page=zero")
        delete_response = self.client.delete("/api/history/999999")

        self.assertEqual(pagination_response.status_code, 400)
        self.assertEqual(
            pagination_response.get_json()["error"]["code"], "invalid_pagination"
        )
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(delete_response.get_json()["error"]["code"], "not_found")

    def test_api_responses_include_security_headers(self) -> None:
        """API responses prevent caching and include browser safety headers."""
        response = self.client.get("/api/dashboard")

        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_history_and_delete_endpoints(self) -> None:
        """History is paginated newest-first and records can be deleted."""
        history_response = self.client.get("/api/history?page=1&per_page=10")
        history_data = history_response.get_json()
        prediction_id = history_data["data"][0]["id"]
        delete_response = self.client.delete(f"/api/history/{prediction_id}")

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_data["pagination"]["total_records"], 1)
        self.assertEqual(delete_response.status_code, 200)

    def test_dashboard_and_statistics_endpoints(self) -> None:
        """Dashboard and statistics return persisted prediction aggregates."""
        dashboard_response = self.client.get("/api/dashboard")
        statistics_response = self.client.get("/api/statistics")

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(
            dashboard_response.get_json()["data"]["total_predictions"],
            1,
        )
        self.assertEqual(statistics_response.status_code, 200)
        self.assertEqual(
            statistics_response.get_json()["data"]["crop_distribution"]["rice"],
            1,
        )

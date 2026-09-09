"""Integration tests for the local model upload and activation workflow."""

import io
import json
import pickle
import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app import create_app
from app.models.database import db
from app.models.user import User
from app.services.model_upload_service import ModelUploadService
from app.services.model_loader import ModelLoader


class ModelUploadTests(unittest.TestCase):
    """Ensure a complete compatible artifact bundle becomes the active model."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.app = create_app("testing")
        self.app.config.update(
            MODEL_UPLOAD_ENABLED=True,
            MODEL_PATH=root / "models",
            PROCESSED_DATA_PATH=root / "processed",
        )
        with self.app.app_context():
            db.create_all()
            self.admin = User(
                name="Model Administrator",
                email="admin@example.com",
                role="admin",
            )
            self.admin.set_password("test-password")
            db.session.add(self.admin)
            db.session.commit()
        self.client = self.app.test_client()

    def _sign_in_as_admin(self) -> None:
        """Create the Flask-Login session required by the upload endpoint."""
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.admin.id)
            session["_fresh"] = True

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temporary_directory.cleanup()

    def test_compatible_upload_activates_and_is_loaded(self) -> None:
        """The endpoint stages, validates, activates, and reloads all artifacts."""
        self._sign_in_as_admin()
        features = np.array(
            [[90, 40, 40, 20, 80, 6.5, 200], [20, 20, 20, 30, 50, 7, 80]]
        )
        labels = LabelEncoder().fit(["rice", "maize"])
        scaler = StandardScaler().fit(features)
        model = RandomForestClassifier(n_estimators=2, random_state=42).fit(
            scaler.transform(features), labels.transform(["rice", "maize"])
        )
        metadata = {
            "algorithm": "Random Forest",
            "dependencies": {
                ("sklearn" if package == "scikit-learn" else package): version(package)
                for package in ("scikit-learn", "joblib", "numpy", "pandas")
            },
        }
        response = self.client.post(
            "/api/model/upload",
            data={
                "model": (io.BytesIO(pickle.dumps(model)), "best_model.pkl"),
                "metadata": (
                    io.BytesIO(json.dumps(metadata).encode()),
                    "model_metadata.json",
                ),
                "label_encoder": (
                    io.BytesIO(pickle.dumps(labels)), "label_encoder.pkl"
                ),
                "scaler": (io.BytesIO(pickle.dumps(scaler)), "scaler.pkl"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "Model activated successfully.")
        self.assertTrue((self.app.config["MODEL_PATH"] / "best_model.pkl").is_file())
        self.assertTrue(
            (self.app.config["PROCESSED_DATA_PATH"] / "label_encoder.pkl").is_file()
        )
        self.assertIsNotNone(self.app.extensions["model_loader"].load().model)
        prediction = self.client.post(
            "/api/predict",
            json={
                "N": 90,
                "P": 40,
                "K": 40,
                "temperature": 20,
                "humidity": 80,
                "ph": 6.5,
                "rainfall": 200,
            },
        )
        self.assertEqual(prediction.status_code, 200)
        self.assertTrue(prediction.get_json()["success"])

    def test_dependency_metadata_supports_aliases_and_common_formats(self) -> None:
        """Aliases, requirements, libraries, and newer patch versions are accepted."""
        self.assertEqual(
            ModelUploadService._required_dependencies(
                {"dependencies": {"sklearn": "1.6.0"}}
            ),
            {"scikit-learn": "1.6.0"},
        )
        self.assertEqual(
            ModelUploadService._required_dependencies(
                {"requirements": ["joblib>=1.4", "numpy"]}
            ),
            {"joblib": ">=1.4", "numpy": None},
        )
        self.assertEqual(
            ModelUploadService._required_dependencies({"libraries": ["pandas"]}),
            {"pandas": None},
        )
        self.assertEqual(
            ModelUploadService._required_dependencies({"framework": "sklearn>=1.6"}),
            {"scikit-learn": ">=1.6"},
        )
        self.assertTrue(ModelUploadService._versions_are_compatible("1.5.2", "1.5.0"))

    def test_loader_supports_joblib_and_pickle_artifacts(self) -> None:
        """The loader accepts either serialization format used by uploaded models."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            joblib_path = root / "joblib.pkl"
            pickle_path = root / "pickle.pkl"
            joblib.dump({"format": "joblib"}, joblib_path)
            with pickle_path.open("wb") as artifact_file:
                pickle.dump({"format": "pickle"}, artifact_file)

            self.assertEqual(ModelLoader._load_pickle(joblib_path)["format"], "joblib")
            self.assertEqual(ModelLoader._load_pickle(pickle_path)["format"], "pickle")

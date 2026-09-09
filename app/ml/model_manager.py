"""Persistence helpers for trained model artifacts and metadata."""

import hashlib
import json
import pickle
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from sklearn.base import ClassifierMixin


class ModelManager:
    """Save trained classifiers and their reproducibility metadata."""

    def __init__(self, models_directory: Path) -> None:
        self.models_directory = models_directory
        self.models_directory.mkdir(parents=True, exist_ok=True)

    def save_model(self, name: str, model: ClassifierMixin) -> Path:
        """Save a named trained model and return its artifact path."""
        model_path = self.models_directory / f"{self._safe_name(name)}.pkl"
        self._write_pickle(model, model_path)
        return model_path

    def save_best_model(self, model: ClassifierMixin) -> Path:
        """Save the selected production candidate using a stable filename."""
        model_path = self.models_directory / "best_model.pkl"
        self._write_pickle(model, model_path)
        return model_path

    def save_metadata(
        self,
        algorithm: str,
        accuracy: float,
        model: ClassifierMixin,
        dataset_path: Path,
        feature_count: int,
    ) -> Path:
        """Write JSON metadata required to reproduce the selected model run."""
        training_timestamp = datetime.now(timezone.utc).isoformat()
        metadata = {
            "algorithm": algorithm,
            "accuracy": round(accuracy, 6),
            "hyperparameters": model.get_params(),
            "dataset_name": dataset_path.name,
            "dataset_version": self.dataset_version(dataset_path),
            "feature_count": feature_count,
            "training_date": training_timestamp,
            "training_timestamp": training_timestamp,
            "dependencies": self._dependency_versions(),
        }
        metadata_path = self.models_directory / "model_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )
        return metadata_path

    @staticmethod
    def _dependency_versions() -> dict[str, str]:
        """Record exact package versions needed to reload the trained model."""
        packages = ("scikit-learn", "joblib", "numpy", "pandas")
        versions = {}
        for package in packages:
            try:
                versions[package] = metadata.version(package)
            except metadata.PackageNotFoundError:
                continue
        return versions

    @staticmethod
    def dataset_version(dataset_path: Path) -> str:
        """Create a content-based version identifier for the processed dataset."""
        digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        return f"sha256:{digest}"

    @staticmethod
    def _safe_name(name: str) -> str:
        """Convert a display name into a predictable artifact filename."""
        return name.lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _write_pickle(artifact: object, output_path: Path) -> None:
        """Persist a binary model artifact to disk."""
        with output_path.open("wb") as artifact_file:
            pickle.dump(artifact, artifact_file)

"""One-time, thread-safe loading of trained prediction artifacts."""

import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from app.utils.exceptions import ModelLoadError, ModelUnavailableError


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelArtifacts:
    """Trained model and preprocessing assets needed for inference."""

    model: Any
    label_encoder: Any
    scaler: Any
    metadata: dict[str, Any]


class ModelLoader:
    """Load model artifacts once and reuse them for every prediction request."""

    def __init__(
        self,
        models_directory: Path = Path("models"),
        processed_directory: Path = Path("data/processed"),
    ) -> None:
        self.models_directory = models_directory
        self.processed_directory = processed_directory
        self._artifacts: ModelArtifacts | None = None
        self._load_error: ModelLoadError | None = None
        self._attempted_load = False
        self._lock = Lock()

    def load(self) -> ModelArtifacts:
        """Load artifacts once; cache both success and failure state."""
        with self._lock:
            if self._artifacts is not None:
                return self._artifacts
            if self._attempted_load:
                raise self._load_error or ModelLoadError("Model loading failed.")

            self._attempted_load = True
            try:
                artifacts = ModelArtifacts(
                    model=self._load_pickle(self.models_directory / "best_model.pkl"),
                    label_encoder=self._load_pickle(
                        self.processed_directory / "label_encoder.pkl"
                    ),
                    scaler=self._load_pickle(self.processed_directory / "scaler.pkl"),
                    metadata=self._load_metadata(
                        self.models_directory / "model_metadata.json"
                    ),
                )
                LOGGER.debug(
                    "Loading prediction artifacts: model=%s scaler=%s label_encoder=%s metadata=%s",
                    self.models_directory / "best_model.pkl",
                    self.processed_directory / "scaler.pkl",
                    self.processed_directory / "label_encoder.pkl",
                    self.models_directory / "model_metadata.json",
                )
                self._validate_artifacts(artifacts)
                self._artifacts = artifacts
                LOGGER.info("Prediction model artifacts loaded successfully.")
                LOGGER.debug(
                    "Loaded artifacts: model_class=%s scaler_type=%s label_classes=%s metadata_version=%s",
                    type(artifacts.model).__name__,
                    type(artifacts.scaler).__name__,
                    getattr(artifacts.label_encoder, "classes_", []).tolist(),
                    artifacts.metadata.get(
                        "model_version",
                        artifacts.metadata.get("version", artifacts.metadata.get("dataset_version")),
                    ),
                )
                return artifacts
            except ModelLoadError as error:
                self._load_error = error
                LOGGER.error("Unable to load prediction artifacts: %s", error)
                raise

    def get_artifacts(self) -> ModelArtifacts:
        """Return cached artifacts or a clear unavailable-model error."""
        if self._artifacts is not None:
            return self._artifacts

        if not self._attempted_load:
            try:
                self.load()
            except ModelLoadError as error:
                raise ModelUnavailableError(
                    "Prediction model is unavailable. Please complete model "
                    "training first."
                ) from error

        raise ModelUnavailableError(
            "Prediction model is unavailable. Please complete model training first."
        ) from self._load_error

    @staticmethod
    def _load_pickle(artifact_path: Path) -> Any:
        """Load a joblib or pickle artifact while preserving useful errors."""
        if not artifact_path.is_file():
            raise ModelLoadError(
                f"Required model artifact is missing: {artifact_path.name}"
            )

        try:
            import joblib
        except ModuleNotFoundError:
            LOGGER.info(
                "Joblib is not installed; loading %s with pickle.",
                artifact_path.name,
            )
        else:
            try:
                artifact = joblib.load(artifact_path)
                LOGGER.info("Loaded %s using joblib.", artifact_path.name)
                return artifact
            except Exception as joblib_error:
                LOGGER.info(
                    "Joblib could not load %s; trying pickle: %s",
                    artifact_path.name,
                    joblib_error,
                )
        try:
            with artifact_path.open("rb") as artifact_file:
                artifact = pickle.load(artifact_file)
            LOGGER.info("Loaded %s using pickle.", artifact_path.name)
            return artifact
        except Exception as error:
            raise ModelLoadError(
                f"Unable to load {artifact_path.name} with joblib or pickle: {error}"
            ) from error

    @staticmethod
    def _load_metadata(metadata_path: Path) -> dict[str, Any]:
        """Load model metadata JSON with corruption handling."""
        if not metadata_path.is_file():
            raise ModelLoadError("Required model metadata is missing.")

        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ModelLoadError("Model metadata is corrupted.") from error

    @staticmethod
    def _validate_artifacts(artifacts: ModelArtifacts) -> None:
        """Ensure required methods exist before serving any prediction."""
        if not hasattr(artifacts.model, "predict"):
            raise ModelLoadError("Loaded model does not support prediction.")
        if not hasattr(artifacts.scaler, "transform"):
            raise ModelLoadError("Loaded scaler does not support transformation.")
        if not hasattr(artifacts.label_encoder, "inverse_transform"):
            raise ModelLoadError("Loaded label encoder cannot decode crop labels.")
        if not hasattr(artifacts.model, "classes_"):
            raise ModelLoadError("Loaded model does not expose its trained classes.")

        model_class_count = len(artifacts.model.classes_)
        encoder_class_count = len(getattr(artifacts.label_encoder, "classes_", []))
        metadata_classes = artifacts.metadata.get("classes")
        metadata_class_count = artifacts.metadata.get(
            "total_classes",
            len(metadata_classes) if isinstance(metadata_classes, list) else None,
        )
        try:
            metadata_class_count = (
                int(metadata_class_count)
                if metadata_class_count is not None
                else encoder_class_count
            )
        except (TypeError, ValueError) as error:
            raise ModelLoadError("Model metadata contains an invalid class count.") from error

        if (
            model_class_count != encoder_class_count
            or model_class_count != metadata_class_count
        ):
            if encoder_class_count == metadata_class_count:
                raise ModelLoadError(
                    "Incompatible model bundle. The uploaded best_model.pkl was "
                    f"trained with {model_class_count} classes, but the uploaded "
                    "label encoder and metadata expect "
                    f"{encoder_class_count} classes."
                )
            raise ModelLoadError(
                "Incompatible model bundle: "
                f"model classes={model_class_count}, "
                f"label encoder classes={encoder_class_count}, "
                f"metadata classes={metadata_class_count}."
            )
        if not hasattr(artifacts.model, "classes_"):
            raise ModelLoadError("Loaded model does not expose its trained classes.")

        encoder_classes = list(getattr(artifacts.label_encoder, "classes_", []))
        model_classes = list(getattr(artifacts.model, "classes_", []))
        expected_codes = set(range(len(encoder_classes)))
        try:
            actual_codes = {int(value) for value in model_classes}
        except (TypeError, ValueError) as error:
            raise ModelLoadError(
                "Model classes must be label-encoder integer codes."
            ) from error
        if actual_codes != expected_codes:
            raise ModelLoadError(
                "Uploaded model and label encoder do not match: "
                f"model has {len(actual_codes)} classes but label encoder has "
                f"{len(encoder_classes)} classes. Upload all artifacts from the same training run."
            )
        expected_features = artifacts.metadata.get(
            "feature_count",
            artifacts.metadata.get("total_features"),
        )
        scaler_features = getattr(artifacts.scaler, "n_features_in_", None)
        model_features = getattr(artifacts.model, "n_features_in_", None)
        if expected_features is not None and (
            scaler_features != expected_features or model_features != expected_features
        ):
            raise ModelLoadError(
                "Uploaded model, scaler, and metadata have incompatible feature counts."
            )

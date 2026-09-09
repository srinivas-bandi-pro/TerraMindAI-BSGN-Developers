"""Stage, validate, and activate model artifacts uploaded through the local UI."""

import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from werkzeug.datastructures import FileStorage


REQUIRED_ARTIFACTS = {
    "model": ("best_model.pkl", "pkl", "models_directory"),
    "metadata": ("model_metadata.json", "json", "models_directory"),
    "label_encoder": ("label_encoder.pkl", "pkl", "processed_directory"),
    "scaler": ("scaler.pkl", "pkl", "processed_directory"),
}
FALLBACK_DEPENDENCIES = ("joblib", "scikit-learn", "numpy", "pandas")
PACKAGE_ALIASES = {
    "sklearn": "scikit-learn",
    "scikit_learn": "scikit-learn",
}
LOGGER = logging.getLogger(__name__)


class ModelUploadError(ValueError):
    """Raised when uploaded artifacts do not meet the required contract."""


@dataclass(frozen=True)
class StagedModelUpload:
    """A complete, validated upload kept outside the active artifact paths."""

    root: Path
    models_directory: Path
    processed_directory: Path
    metadata: dict[str, Any]


class ModelUploadService:
    """Validate model uploads before replacing the current active model."""

    def __init__(self, models_directory: Path, processed_directory: Path) -> None:
        self.models_directory = models_directory
        self.processed_directory = processed_directory

    def stage(self, files: dict[str, FileStorage]) -> StagedModelUpload:
        """Store one upload in a temporary bundle and check its dependencies."""
        self.models_directory.mkdir(parents=True, exist_ok=True)
        staging_root = Path(
            tempfile.mkdtemp(prefix=".model-upload-", dir=self.models_directory)
        )
        staged_models = staging_root / "models"
        staged_processed = staging_root / "processed"
        try:
            for field, (destination_name, suffix, directory_name) in REQUIRED_ARTIFACTS.items():
                uploaded_file = files.get(field)
                if field != "metadata" and (
                    uploaded_file is None or not uploaded_file.filename
                ):
                    raise ModelUploadError(f"Select the {destination_name} file.")
                if field == "metadata" and (
                    uploaded_file is None or not uploaded_file.filename
                ):
                    (staged_models / destination_name).write_text("{}", encoding="utf-8")
                    continue
                if not uploaded_file.filename.lower().endswith(f".{suffix}"):
                    raise ModelUploadError(f"{destination_name} must be a .{suffix} file.")
                directory = staged_models if directory_name == "models_directory" else staged_processed
                directory.mkdir(parents=True, exist_ok=True)
                destination_path = directory / destination_name
                uploaded_file.save(destination_path)
                if destination_path.stat().st_size == 0:
                    raise ModelUploadError(f"{destination_name} cannot be empty.")
            metadata_path = staged_models / "model_metadata.json"
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                LOGGER.warning(
                    "Uploaded model metadata was invalid; using fallback dependencies."
                )
                metadata = {}
                metadata_path.write_text("{}", encoding="utf-8")
            if not isinstance(metadata, dict):
                LOGGER.warning(
                    "Uploaded model metadata was not an object; using fallback dependencies."
                )
                metadata = {}
                metadata_path.write_text("{}", encoding="utf-8")
            self._validate_dependencies(metadata)
            return StagedModelUpload(
                root=staging_root,
                models_directory=staged_models,
                processed_directory=staged_processed,
                metadata=metadata,
            )
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise

    def activate(self, staged_upload: StagedModelUpload) -> None:
        """Replace active artifacts only after the staged bundle has loaded."""
        self.models_directory.mkdir(parents=True, exist_ok=True)
        self.processed_directory.mkdir(parents=True, exist_ok=True)
        replacements = (
            (staged_upload.models_directory / "best_model.pkl", self.models_directory / "best_model.pkl"),
            (staged_upload.models_directory / "model_metadata.json", self.models_directory / "model_metadata.json"),
            (staged_upload.processed_directory / "label_encoder.pkl", self.processed_directory / "label_encoder.pkl"),
            (staged_upload.processed_directory / "scaler.pkl", self.processed_directory / "scaler.pkl"),
        )
        backup_directory = staged_upload.root / "previous"
        activated: list[tuple[Path, Path]] = []
        try:
            backup_directory.mkdir()
            for source, destination in replacements:
                backup = backup_directory / destination.name
                if destination.exists():
                    os.replace(destination, backup)
                os.replace(source, destination)
                activated.append((destination, backup))
        except OSError as error:
            for destination, backup in reversed(activated):
                destination.unlink(missing_ok=True)
                if backup.exists():
                    os.replace(backup, destination)
            for _, destination in replacements:
                backup = backup_directory / destination.name
                if backup.exists() and not destination.exists():
                    os.replace(backup, destination)
            raise ModelUploadError(f"Could not activate uploaded model: {error}") from error
        finally:
            shutil.rmtree(staged_upload.root, ignore_errors=True)

    @staticmethod
    def discard(staged_upload: StagedModelUpload) -> None:
        """Remove a staged upload that did not pass model loading validation."""
        shutil.rmtree(staged_upload.root, ignore_errors=True)

    @staticmethod
    def _validate_dependencies(model_metadata: dict[str, Any]) -> None:
        """Validate metadata dependencies against this Flask process environment."""
        required = ModelUploadService._required_dependencies(model_metadata)
        LOGGER.info("Required upload packages: %s", required)
        missing: list[str] = []
        incompatible: list[str] = []
        installed: dict[str, str] = {}
        for package, expected_version in required.items():
            try:
                installed_version = ModelUploadService._installed_version(package)
            except metadata.PackageNotFoundError:
                missing.append(package)
                LOGGER.warning(
                    "Dependency comparison: package=%s installed=not found required=%s result=missing",
                    package,
                    expected_version or "any",
                )
                continue
            installed[package] = installed_version
            LOGGER.info(
                "Dependency comparison: package=%s installed=%s required=%s result=%s",
                package,
                installed_version,
                expected_version or "any",
                "compatible"
                if not expected_version
                or ModelUploadService._versions_are_compatible(
                    installed_version, expected_version
                )
                else "incompatible",
            )
            if expected_version and not ModelUploadService._versions_are_compatible(
                installed_version, expected_version
            ):
                incompatible.append(
                    f"{package} (requires {expected_version}; installed {installed_version})"
                )
        LOGGER.info("Installed upload packages: %s", installed)
        if missing:
            LOGGER.warning(
                "Distribution metadata did not find %s. Continuing to staged model "
                "load, which is the authoritative compatibility check.",
                ", ".join(sorted(missing)),
            )
        if incompatible:
            LOGGER.warning(
                "Metadata reports version differences (%s). Continuing to staged "
                "model load, which verifies actual compatibility.",
                "; ".join(incompatible),
            )

    @staticmethod
    def _required_dependencies(model_metadata: dict[str, Any]) -> dict[str, str | None]:
        """Read common dependency schemas, defaulting only when none are supplied."""
        for key in (
            "dependencies",
            "required_dependencies",
            "package_versions",
            "requirements",
            "libraries",
            "framework",
        ):
            declared = model_metadata.get(key)
            if isinstance(declared, dict) and declared:
                return {
                    ModelUploadService._canonical_package_name(str(package)): (
                        str(value) if value else None
                    )
                    for package, value in declared.items()
                }
            if isinstance(declared, (list, tuple)) and declared:
                return ModelUploadService._parse_requirement_list(declared)
            if isinstance(declared, str) and declared.strip():
                return ModelUploadService._parse_requirement_list([declared])
        LOGGER.info("No dependency metadata supplied; using fallback package checks.")
        return {package: None for package in FALLBACK_DEPENDENCIES}

    @staticmethod
    def _installed_version(package: str) -> str:
        """Read a distribution version, accepting common package-name spellings."""
        canonical = ModelUploadService._canonical_package_name(package)
        candidates = (canonical, canonical.replace("-", "_"))
        for candidate in candidates:
            try:
                return metadata.version(candidate)
            except metadata.PackageNotFoundError:
                continue
        raise metadata.PackageNotFoundError(canonical)

    @staticmethod
    def _parse_requirement_list(items: list[Any] | tuple[Any, ...]) -> dict[str, str | None]:
        """Parse simple requirement strings such as ``sklearn>=1.6``."""
        dependencies: dict[str, str | None] = {}
        for item in items:
            requirement = str(item).strip()
            for marker in (">=", "<=", "==", "~=", ">", "<"):
                if marker in requirement:
                    package, required_version = requirement.split(marker, 1)
                    dependencies[ModelUploadService._canonical_package_name(package)] = (
                        marker + required_version.strip()
                    )
                    break
            else:
                dependencies[ModelUploadService._canonical_package_name(requirement)] = None
        return dependencies

    @staticmethod
    def _canonical_package_name(package: str) -> str:
        """Map Python module aliases to the package distribution name."""
        normalized = package.strip().lower().replace("_", "-")
        return PACKAGE_ALIASES.get(normalized, normalized)

    @staticmethod
    def _versions_are_compatible(installed: str, required: str) -> bool:
        """Accept compatible newer patch/minor releases without exact pinning."""
        try:
            installed_version = Version(installed)
            constraint = required.strip()
            if constraint.startswith("=="):
                constraint = constraint[2:].strip()
                required_version = Version(constraint)
                return (
                    installed_version.major == required_version.major
                    and installed_version >= required_version
                )
            if constraint.startswith((">", "<", "=", "~", "!")) or "," in constraint:
                return installed_version in SpecifierSet(constraint)
            required_version = Version(constraint)
            return (
                installed_version.major == required_version.major
                and installed_version >= required_version
            )
        except (InvalidVersion, InvalidSpecifier):
            LOGGER.warning(
                "Could not compare dependency versions safely: installed=%s required=%s",
                installed,
                required,
            )
            return False

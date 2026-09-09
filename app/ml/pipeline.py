"""Configurable preprocessing pipeline for crop recommendation data."""

import argparse
import logging
from dataclasses import dataclass
from math import ceil
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from app.ml.dataset_loader import FEATURE_COLUMNS, TARGET_COLUMN, load_dataset
from app.ml.preprocessing import (
    OutlierReport,
    create_scaler,
    detect_iqr_outliers,
    encode_labels,
    find_duplicate_count,
    handle_missing_values,
    remove_duplicates,
    report_missing_values,
    save_artifact,
)
from app.ml.validators import validate_dataset


LOGGER = logging.getLogger(__name__)
DEFAULT_DATASET_PATH = Path("data/raw/Crop_recommendation.csv")


@dataclass(frozen=True)
class PreprocessingConfig:
    """Configuration controlling preprocessing behaviour and output locations."""

    scaler_name: str = "standard"
    remove_outliers: bool = False
    test_size: float = 0.20
    random_state: int = 42
    processed_directory: Path = Path("data/processed")
    reports_directory: Path = Path("reports")


@dataclass
class PreprocessingResult:
    """Prepared datasets and data-quality metrics from one pipeline run."""

    processed_dataset: pd.DataFrame
    x_train: pd.DataFrame
    x_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    original_records: int
    records_processed: int
    duplicates_removed: int
    target_rows_removed: int
    missing_values: dict[str, int]
    outlier_report: OutlierReport
    scaler_name: str
    class_names: list[str]


class CropPreprocessingPipeline:
    """Prepare raw crop data consistently without fitting an ML model."""

    def __init__(self, config: PreprocessingConfig | None = None) -> None:
        self.config = config or PreprocessingConfig()

    def run(self, dataset_path: str | Path) -> PreprocessingResult:
        """Validate, clean, split, scale, encode, and save preprocessing assets."""
        configure_preprocessing_logging(self.config.reports_directory)
        dataset = load_dataset(dataset_path)
        validate_dataset(dataset)
        original_records = len(dataset)
        dataset = dataset.loc[:, (*FEATURE_COLUMNS, TARGET_COLUMN)].copy()

        duplicates_removed = find_duplicate_count(dataset)
        dataset = remove_duplicates(dataset)
        LOGGER.info("Removed %d duplicate records.", duplicates_removed)

        missing_values = report_missing_values(dataset)
        dataset, target_rows_removed = handle_missing_values(dataset)
        LOGGER.info("Missing values before handling: %s", missing_values)
        LOGGER.info(
            "Applied median imputation to missing numeric feature values."
        )
        LOGGER.info("Removed %d records with missing labels.", target_rows_removed)

        outlier_report = detect_iqr_outliers(dataset)
        outlier_rows = int(outlier_report.row_mask.sum())
        LOGGER.info(
            "Detected %d rows with IQR outliers: %s",
            outlier_rows,
            outlier_report.feature_counts,
        )
        if self.config.remove_outliers:
            dataset = dataset.loc[~outlier_report.row_mask].copy()
            LOGGER.warning("Removed %d outlier rows by configuration.", outlier_rows)

        self._validate_training_readiness(dataset)
        encoded_labels, encoder = encode_labels(dataset[TARGET_COLUMN])
        train_index, test_index = self._split_indices(dataset, encoded_labels)

        scaler = create_scaler(self.config.scaler_name)
        training_features = dataset.loc[train_index, FEATURE_COLUMNS]
        scaler.fit(training_features)
        scaled_features = pd.DataFrame(
            scaler.transform(dataset.loc[:, FEATURE_COLUMNS]),
            columns=FEATURE_COLUMNS,
            index=dataset.index,
        )
        processed_dataset = scaled_features.copy()
        processed_dataset[TARGET_COLUMN] = encoded_labels

        x_train = processed_dataset.loc[train_index, FEATURE_COLUMNS]
        x_test = processed_dataset.loc[test_index, FEATURE_COLUMNS]
        y_train = processed_dataset.loc[train_index, TARGET_COLUMN]
        y_test = processed_dataset.loc[test_index, TARGET_COLUMN]

        result = PreprocessingResult(
            processed_dataset=processed_dataset,
            x_train=x_train,
            x_test=x_test,
            y_train=y_train,
            y_test=y_test,
            original_records=original_records,
            records_processed=len(processed_dataset),
            duplicates_removed=duplicates_removed,
            target_rows_removed=target_rows_removed,
            missing_values=missing_values,
            outlier_report=outlier_report,
            scaler_name=self.config.scaler_name,
            class_names=encoder.classes_.tolist(),
        )
        self._save_outputs(result, scaler, encoder)
        return result

    def _split_indices(
        self,
        dataset: pd.DataFrame,
        encoded_labels: pd.Series,
    ) -> tuple[pd.Index, pd.Index]:
        """Create a reproducible 80/20 split, stratifying when possible."""
        label_counts = encoded_labels.value_counts()
        test_records = max(1, ceil(len(dataset) * self.config.test_size))
        can_stratify = (
            label_counts.min() >= 2
            and test_records >= len(label_counts)
            and len(dataset) - test_records >= len(label_counts)
        )
        stratify_labels = encoded_labels if can_stratify else None

        if not can_stratify:
            LOGGER.warning(
                "Dataset is too small for a stratified split; using a random split."
            )

        train_index, test_index = train_test_split(
            dataset.index,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=stratify_labels,
        )
        return pd.Index(train_index), pd.Index(test_index)

    @staticmethod
    def _validate_training_readiness(dataset: pd.DataFrame) -> None:
        """Verify enough clean records and classes remain for a future split."""
        if len(dataset) < 2:
            raise ValueError("At least two clean records are required for splitting.")
        if dataset[TARGET_COLUMN].nunique() < 2:
            raise ValueError("At least two crop labels are required for splitting.")

    def _save_outputs(
        self,
        result: PreprocessingResult,
        scaler: object,
        encoder: object,
    ) -> None:
        """Save the processed data, fitted artifacts, and Markdown report."""
        self.config.processed_directory.mkdir(parents=True, exist_ok=True)
        processed_path = self.config.processed_directory / "processed_dataset.csv"
        result.processed_dataset.to_csv(processed_path, index=False)
        save_artifact(
            encoder,
            self.config.processed_directory / "label_encoder.pkl",
        )
        save_artifact(scaler, self.config.processed_directory / "scaler.pkl")
        self._write_report(result)
        LOGGER.info(
            "Saved preprocessing artifacts to %s",
            self.config.processed_directory,
        )

    def _write_report(self, result: PreprocessingResult) -> None:
        """Write a Markdown summary of the completed preprocessing run."""
        self.config.reports_directory.mkdir(parents=True, exist_ok=True)
        report_path = self.config.reports_directory / "preprocessing_report.md"
        outlier_rows = int(result.outlier_report.row_mask.sum())
        missing_lines = "\n".join(
            f"- `{column}`: {count}" for column, count in result.missing_values.items()
        )
        outlier_lines = "\n".join(
            f"- `{column}`: {count}"
            for column, count in result.outlier_report.feature_counts.items()
        )
        report = f"""# AgriSmart AI Preprocessing Report

## Dataset Size

- Original records: {result.original_records}
- Records processed: {result.records_processed}
- Train/test split: 80% / 20% (random state 42)

## Duplicate Handling

- Duplicates removed: {result.duplicates_removed}

## Missing Values

{missing_lines}

- Strategy: median imputation for numeric features; rows missing `label` removed.
- Rows removed for missing label: {result.target_rows_removed}

## Outliers

- IQR-flagged rows: {outlier_rows}
- Automatic removal enabled: {self.config.remove_outliers}

{outlier_lines}

## Scaling and Encoding

- Scaler: {result.scaler_name}
- Label encoder: `LabelEncoder`
- Encoded crop classes: {len(result.class_names)}

## Recommendations

- Review IQR-flagged records with agricultural domain knowledge before removal.
- Keep preprocessing artifacts paired with any future trained model.
- Re-run preprocessing whenever the raw dataset changes.
"""
        report_path.write_text(report, encoding="utf-8")


def configure_preprocessing_logging(reports_directory: Path) -> None:
    """Write preprocessing events to a reusable file logger."""
    reports_directory.mkdir(parents=True, exist_ok=True)
    log_path = reports_directory / "preprocessing.log"

    if any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_path.resolve()
        for handler in LOGGER.handlers
    ):
        return

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def main() -> None:
    """Run preprocessing from the command line without training a model."""
    parser = argparse.ArgumentParser(
        description="Preprocess Crop Recommendation data without model training."
    )
    parser.add_argument("dataset_path", nargs="?", default=DEFAULT_DATASET_PATH)
    parser.add_argument("--scaler", choices=("standard", "minmax"), default="standard")
    parser.add_argument("--remove-outliers", action="store_true")
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    configuration = PreprocessingConfig(
        scaler_name=arguments.scaler,
        remove_outliers=arguments.remove_outliers,
    )
    configure_preprocessing_logging(configuration.reports_directory)

    try:
        CropPreprocessingPipeline(configuration).run(arguments.dataset_path)
    except (FileNotFoundError, ValueError, OSError) as error:
        LOGGER.error("Preprocessing could not be completed: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

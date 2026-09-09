"""Validation rules for crop recommendation preprocessing."""

from dataclasses import dataclass

import pandas as pd

from app.ml.dataset_loader import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    detect_invalid_data_types,
    numeric_features,
    validate_required_columns,
)


class PreprocessingValidationError(ValueError):
    """Raised when data is unsafe to pass into preprocessing."""


@dataclass(frozen=True)
class FeatureRange:
    """Inclusive physical limits for one crop recommendation feature."""

    minimum: float
    maximum: float | None = None


FEATURE_RANGES = {
    "N": FeatureRange(minimum=0),
    "P": FeatureRange(minimum=0),
    "K": FeatureRange(minimum=0),
    "temperature": FeatureRange(minimum=-50, maximum=70),
    "humidity": FeatureRange(minimum=0, maximum=100),
    "ph": FeatureRange(minimum=0, maximum=14),
    "rainfall": FeatureRange(minimum=0),
}


def validate_dataset(dataset: pd.DataFrame) -> None:
    """Validate structure, types, and physically impossible feature values."""
    validate_required_columns(dataset)

    if dataset.empty:
        raise PreprocessingValidationError("The dataset contains no records.")

    validate_data_types(dataset)
    validate_feature_ranges(dataset)
    validate_labels(dataset)


def validate_data_types(dataset: pd.DataFrame) -> None:
    """Reject non-numeric feature values and non-text crop labels."""
    invalid_counts = detect_invalid_data_types(dataset)
    invalid_columns = {
        column: count
        for column, count in invalid_counts.items()
        if count > 0
    }

    if invalid_columns:
        details = ", ".join(
            f"{column}: {count}" for column, count in invalid_columns.items()
        )
        raise PreprocessingValidationError(
            f"Invalid data types detected ({details})."
        )


def validate_feature_ranges(dataset: pd.DataFrame) -> None:
    """Reject non-missing feature values outside plausible physical limits."""
    numeric_dataset = numeric_features(dataset)
    invalid_values: dict[str, int] = {}

    for column, limits in FEATURE_RANGES.items():
        values = numeric_dataset[column]
        invalid_mask = values.notna() & (values < limits.minimum)

        if limits.maximum is not None:
            invalid_mask |= values.notna() & (values > limits.maximum)

        invalid_values[column] = int(invalid_mask.sum())

    failed_columns = {
        column: count for column, count in invalid_values.items() if count > 0
    }
    if failed_columns:
        details = ", ".join(
            f"{column}: {count}" for column, count in failed_columns.items()
        )
        raise PreprocessingValidationError(
            f"Impossible feature values detected ({details})."
        )


def validate_labels(dataset: pd.DataFrame) -> None:
    """Reject blank crop labels while allowing missing labels to be handled later."""
    labels = dataset[TARGET_COLUMN]
    blank_labels = labels.notna() & labels.astype(str).str.strip().eq("")

    if blank_labels.any():
        raise PreprocessingValidationError(
            f"Blank crop labels detected: {int(blank_labels.sum())}."
        )

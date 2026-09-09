"""Safe loading and validation helpers for the crop recommendation dataset."""

import logging
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger(__name__)

FEATURE_COLUMNS = (
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
)
TARGET_COLUMN = "label"
REQUIRED_COLUMNS = (*FEATURE_COLUMNS, TARGET_COLUMN)


class DatasetValidationError(ValueError):
    """Raised when a dataset cannot be used for crop analysis."""


def load_dataset(dataset_path: str | Path) -> pd.DataFrame:
    """Load a CSV dataset and validate that its expected columns are present."""
    csv_path = Path(dataset_path)

    if not csv_path.is_file():
        raise FileNotFoundError(f"Dataset file was not found: {csv_path}")

    try:
        dataset = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as error:
        raise DatasetValidationError("The dataset CSV is empty.") from error
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as error:
        raise DatasetValidationError(
            f"Unable to read dataset CSV: {error}"
        ) from error

    # Whitespace-only header differences are safe to correct before validation.
    dataset.columns = dataset.columns.str.strip()
    validate_required_columns(dataset)

    if dataset.empty:
        raise DatasetValidationError("The dataset contains headers but no rows.")

    LOGGER.info("Loaded dataset with %d rows and %d columns.", *dataset.shape)
    return dataset


def validate_required_columns(dataset: pd.DataFrame) -> None:
    """Ensure the dataset contains every required feature and target column."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(dataset.columns))

    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise DatasetValidationError(
            f"Dataset is missing required columns: {missing_text}"
        )


def detect_invalid_data_types(dataset: pd.DataFrame) -> dict[str, int]:
    """Count feature values that cannot be interpreted as numeric values."""
    invalid_counts: dict[str, int] = {}

    for column in FEATURE_COLUMNS:
        numeric_values = pd.to_numeric(dataset[column], errors="coerce")
        invalid_values = dataset[column].notna() & numeric_values.isna()
        invalid_counts[column] = int(invalid_values.sum())

    non_string_labels = dataset[TARGET_COLUMN].notna() & ~dataset[
        TARGET_COLUMN
    ].map(lambda value: isinstance(value, str))
    invalid_counts[TARGET_COLUMN] = int(non_string_labels.sum())
    return invalid_counts


def numeric_features(dataset: pd.DataFrame) -> pd.DataFrame:
    """Return a numeric analysis view without changing the raw dataset."""
    return dataset.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")

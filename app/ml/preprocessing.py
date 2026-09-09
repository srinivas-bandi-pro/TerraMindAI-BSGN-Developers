"""Reusable preprocessing functions for the crop recommendation dataset."""

import pickle
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from app.ml.dataset_loader import FEATURE_COLUMNS, TARGET_COLUMN, numeric_features


@dataclass(frozen=True)
class OutlierReport:
    """IQR outlier counts and row mask for a dataset."""

    feature_counts: dict[str, int]
    row_mask: pd.Series


def find_duplicate_count(dataset: pd.DataFrame) -> int:
    """Return the number of duplicated rows in a dataset."""
    return int(dataset.duplicated().sum())


def remove_duplicates(dataset: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with duplicated records removed, keeping the first row."""
    return dataset.drop_duplicates().copy()


def report_missing_values(dataset: pd.DataFrame) -> dict[str, int]:
    """Count missing values for every required feature and the target label."""
    required_columns = (*FEATURE_COLUMNS, TARGET_COLUMN)
    missing_counts = dataset.loc[:, required_columns].isna().sum()
    return {column: int(count) for column, count in missing_counts.items()}


def handle_missing_values(dataset: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Median-impute features and drop records with a missing target label."""
    prepared_dataset = dataset.copy()
    missing_target_rows = int(prepared_dataset[TARGET_COLUMN].isna().sum())
    prepared_dataset = prepared_dataset.dropna(subset=[TARGET_COLUMN]).copy()

    for column in FEATURE_COLUMNS:
        numeric_column = pd.to_numeric(prepared_dataset[column], errors="raise")
        median_value = numeric_column.median()

        if pd.isna(median_value):
            raise ValueError(
                f"Cannot impute '{column}' because it contains only missing values."
            )

        prepared_dataset[column] = numeric_column.fillna(median_value)

    prepared_dataset[TARGET_COLUMN] = prepared_dataset[TARGET_COLUMN].str.strip()
    return prepared_dataset, missing_target_rows


def detect_iqr_outliers(dataset: pd.DataFrame) -> OutlierReport:
    """Identify potential outliers using 1.5 times the IQR for each feature."""
    feature_counts: dict[str, int] = {}
    row_mask = pd.Series(False, index=dataset.index)
    features = numeric_features(dataset)

    for column in FEATURE_COLUMNS:
        values = features[column]
        first_quartile = values.quantile(0.25)
        third_quartile = values.quantile(0.75)
        interquartile_range = third_quartile - first_quartile
        lower_bound = first_quartile - 1.5 * interquartile_range
        upper_bound = third_quartile + 1.5 * interquartile_range
        feature_mask = (values < lower_bound) | (values > upper_bound)
        feature_counts[column] = int(feature_mask.sum())
        row_mask |= feature_mask

    return OutlierReport(feature_counts=feature_counts, row_mask=row_mask)


def create_scaler(scaler_name: str) -> StandardScaler | MinMaxScaler:
    """Create the configured feature scaler."""
    normalized_name = scaler_name.strip().lower()

    if normalized_name == "standard":
        return StandardScaler()
    if normalized_name == "minmax":
        return MinMaxScaler()

    raise ValueError("Scaler must be either 'standard' or 'minmax'.")


def encode_labels(labels: pd.Series) -> tuple[pd.Series, LabelEncoder]:
    """Fit a label encoder and return integer-encoded crop labels."""
    encoder = LabelEncoder()
    encoded_values = encoder.fit_transform(labels)
    encoded_labels = pd.Series(encoded_values, index=labels.index, name=TARGET_COLUMN)
    return encoded_labels, encoder


def decode_labels(
    encoded_labels: pd.Series | list[int],
    encoder: LabelEncoder,
) -> list[str]:
    """Convert encoded crop labels back to their original crop names."""
    return encoder.inverse_transform(encoded_labels).tolist()


def save_artifact(artifact: object, output_path: Path) -> None:
    """Persist one fitted preprocessing artifact using Python pickle."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as artifact_file:
        pickle.dump(artifact, artifact_file)

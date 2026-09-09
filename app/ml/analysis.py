"""Orchestrate non-destructive EDA for the crop recommendation dataset."""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.ml.dataset_loader import (
    FEATURE_COLUMNS,
    REQUIRED_COLUMNS,
    TARGET_COLUMN,
    detect_invalid_data_types,
    load_dataset,
    numeric_features,
)
from app.ml.eda import (
    create_boxplots,
    create_class_distribution_chart,
    create_correlation_heatmap,
    create_feature_histograms,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_DATASET_PATH = Path("data/raw/Crop_recommendation.csv")
DEFAULT_CHARTS_DIRECTORY = Path("reports/charts")
DEFAULT_REPORT_PATH = Path("reports/dataset_analysis_report.txt")


@dataclass(frozen=True)
class AnalysisResult:
    """Structured output from an exploratory dataset analysis run."""

    row_count: int
    column_count: int
    missing_values: dict[str, int]
    duplicate_rows: int
    invalid_data_types: dict[str, int]
    outlier_counts: dict[str, int]
    recommendations: list[str]


def identify_outliers(dataset: pd.DataFrame) -> dict[str, int]:
    """Count potential outliers per feature using the IQR method."""
    outlier_counts: dict[str, int] = {}
    features = numeric_features(dataset)

    for column in FEATURE_COLUMNS:
        values = features[column].dropna()
        first_quartile = values.quantile(0.25)
        third_quartile = values.quantile(0.75)
        interquartile_range = third_quartile - first_quartile
        lower_bound = first_quartile - 1.5 * interquartile_range
        upper_bound = third_quartile + 1.5 * interquartile_range
        outliers = values[(values < lower_bound) | (values > upper_bound)]
        outlier_counts[column] = int(outliers.count())

    return outlier_counts


def build_recommendations(
    missing_values: dict[str, int],
    duplicate_rows: int,
    invalid_data_types: dict[str, int],
    outlier_counts: dict[str, int],
) -> list[str]:
    """Create preprocessing recommendations without changing the source data."""
    recommendations = [
        "Keep the raw CSV unchanged and perform cleaning on a processed copy.",
        "Review feature units and valid agronomic ranges before model training.",
        "Use a stratified train/test split only after data-quality issues are resolved.",
    ]

    if any(missing_values.values()):
        recommendations.append(
            "Choose feature-specific missing-value handling after inspecting "
            "missingness patterns."
        )
    if duplicate_rows:
        recommendations.append(
            "Review duplicate records and remove only confirmed duplicate samples."
        )
    if any(invalid_data_types.values()):
        recommendations.append(
            "Convert invalid numeric entries to missing values and investigate "
            "their source before imputation."
        )
    if any(outlier_counts.values()):
        recommendations.append(
            "Review IQR-flagged outliers with domain knowledge; do not remove "
            "valid extreme weather or soil observations automatically."
        )

    return recommendations


def build_analysis_result(dataset: pd.DataFrame) -> AnalysisResult:
    """Calculate data-quality and outlier metrics for the loaded dataset."""
    missing_values = dataset.loc[:, REQUIRED_COLUMNS].isna().sum().astype(int)
    duplicate_rows = int(dataset.duplicated().sum())
    invalid_data_types = detect_invalid_data_types(dataset)
    outlier_counts = identify_outliers(dataset)
    recommendations = build_recommendations(
        missing_values.to_dict(),
        duplicate_rows,
        invalid_data_types,
        outlier_counts,
    )

    return AnalysisResult(
        row_count=len(dataset),
        column_count=len(dataset.columns),
        missing_values=missing_values.to_dict(),
        duplicate_rows=duplicate_rows,
        invalid_data_types=invalid_data_types,
        outlier_counts=outlier_counts,
        recommendations=recommendations,
    )


def write_text_report(
    dataset: pd.DataFrame,
    result: AnalysisResult,
    output_path: Path,
) -> None:
    """Write dataset and statistical summaries to a readable text report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    statistical_summary = numeric_features(dataset).describe().transpose()
    class_distribution = dataset[TARGET_COLUMN].value_counts(dropna=False)

    report_lines = [
        "AgriSmart AI - Crop Recommendation Dataset Analysis",
        "=" * 55,
        f"Rows: {result.row_count}",
        f"Columns: {result.column_count}",
        "",
        "Column data types:",
        dataset.dtypes.to_string(),
        "",
        "Missing values:",
        pd.Series(result.missing_values).to_string(),
        "",
        f"Duplicate rows: {result.duplicate_rows}",
        "",
        "Invalid data-type counts:",
        pd.Series(result.invalid_data_types).to_string(),
        "",
        "Class distribution:",
        class_distribution.to_string(),
        "",
        "Statistical summary:",
        statistical_summary.to_string(),
        "",
        "IQR outlier counts:",
        pd.Series(result.outlier_counts).to_string(),
        "",
        "Recommendations before preprocessing:",
        *[f"- {recommendation}" for recommendation in result.recommendations],
    ]
    output_path.write_text("\n".join(report_lines), encoding="utf-8")


def run_eda(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    charts_directory: Path = DEFAULT_CHARTS_DIRECTORY,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> AnalysisResult:
    """Run validation and EDA, then save charts and a text report."""
    dataset = load_dataset(dataset_path)
    charts_directory.mkdir(parents=True, exist_ok=True)
    result = build_analysis_result(dataset)

    create_class_distribution_chart(
        dataset,
        charts_directory / "class_distribution.png",
    )
    create_feature_histograms(
        dataset,
        charts_directory / "feature_histograms.png",
    )
    create_correlation_heatmap(
        dataset,
        charts_directory / "correlation_heatmap.png",
    )
    create_boxplots(dataset, charts_directory / "boxplots.png")
    write_text_report(dataset, result, report_path)

    LOGGER.info("EDA completed. Charts saved to %s", charts_directory)
    for recommendation in result.recommendations:
        LOGGER.info("Preprocessing recommendation: %s", recommendation)

    return result


def main() -> None:
    """Run EDA from the command line with an optional dataset path."""
    parser = argparse.ArgumentParser(
        description="Analyse the Crop Recommendation dataset without training."
    )
    parser.add_argument(
        "dataset_path",
        nargs="?",
        default=DEFAULT_DATASET_PATH,
        type=Path,
        help="Path to the Crop Recommendation CSV file.",
    )
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    try:
        run_eda(arguments.dataset_path)
    except (FileNotFoundError, ValueError) as error:
        LOGGER.error("EDA could not be completed: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

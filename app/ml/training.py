"""Train, compare, and persist crop recommendation classification models."""

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from app.ml.dataset_loader import FEATURE_COLUMNS, TARGET_COLUMN
from app.ml.evaluation import (
    ModelEvaluation,
    create_comparison_table,
    evaluate_classifier,
    save_evaluation_charts,
)
from app.ml.model_manager import ModelManager
from app.ml.models import build_classifiers


LOGGER = logging.getLogger(__name__)
DEFAULT_DATASET_PATH = Path("data/processed/processed_dataset.csv")


@dataclass(frozen=True)
class TrainingConfig:
    """Configuration for reproducible model training and artifact output."""

    dataset_path: Path = DEFAULT_DATASET_PATH
    models_directory: Path = Path("models")
    reports_directory: Path = Path("reports")
    test_size: float = 0.20
    random_state: int = 42


@dataclass
class TrainingResult:
    """Results from a complete multi-model training run."""

    comparison_table: pd.DataFrame
    best_model: ModelEvaluation
    highest_accuracy_model: ModelEvaluation
    fastest_model: ModelEvaluation


class CropModelTrainingPipeline:
    """Train and compare classifiers using the preprocessed crop dataset."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()

    def run(self) -> TrainingResult:
        """Load processed data, evaluate every model, and save all outputs."""
        configure_training_logging(self.config.reports_directory)
        dataset = self._load_processed_dataset(self.config.dataset_path)
        x_train, x_test, y_train, y_test = self._split_dataset(dataset)
        evaluations = self._train_models(x_train, x_test, y_train, y_test)
        comparison_table = create_comparison_table(evaluations)
        best_model = self._select_best_model(evaluations)
        highest_accuracy_model = max(evaluations, key=lambda item: item.accuracy)
        fastest_model = min(
            evaluations,
            key=lambda item: item.training_time_seconds + item.prediction_time_seconds,
        )

        self._save_artifacts(evaluations, best_model)
        self._save_evaluation_details(evaluations)
        save_evaluation_charts(
            evaluations,
            list(FEATURE_COLUMNS),
            x_test,
            y_test,
            best_model,
            self.config.reports_directory / "charts",
            self.config.random_state,
        )
        result = TrainingResult(
            comparison_table=comparison_table,
            best_model=best_model,
            highest_accuracy_model=highest_accuracy_model,
            fastest_model=fastest_model,
        )
        self._write_report(result, len(dataset))
        LOGGER.info(
            "Training complete. Best model: %s (accuracy %.4f).",
            best_model.name,
            best_model.accuracy,
        )
        return result

    def _load_processed_dataset(self, dataset_path: Path) -> pd.DataFrame:
        """Load and validate the CSV created by the preprocessing pipeline."""
        if not dataset_path.is_file():
            raise FileNotFoundError(
                "Processed dataset was not found. Run preprocessing before "
                f"training: {dataset_path}"
            )

        try:
            dataset = pd.read_csv(dataset_path)
        except (OSError, UnicodeDecodeError, pd.errors.ParserError) as error:
            raise ValueError(f"Unable to read processed dataset: {error}") from error

        required_columns = (*FEATURE_COLUMNS, TARGET_COLUMN)
        missing_columns = sorted(set(required_columns) - set(dataset.columns))
        if missing_columns:
            raise ValueError(
                "Processed dataset is missing required columns: "
                f"{', '.join(missing_columns)}"
            )
        if dataset.empty:
            raise ValueError("Processed dataset contains no records.")
        if dataset.loc[:, required_columns].isna().any().any():
            raise ValueError("Processed dataset contains missing values.")

        numeric_dataset = dataset.loc[:, required_columns].apply(
            pd.to_numeric,
            errors="coerce",
        )
        if numeric_dataset.isna().any().any():
            raise ValueError("Processed dataset contains non-numeric values.")
        if numeric_dataset[TARGET_COLUMN].nunique() < 2:
            raise ValueError("At least two encoded crop labels are required.")

        return numeric_dataset

    def _split_dataset(
        self,
        dataset: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Create the required reproducible 80/20 stratified split."""
        features = dataset.loc[:, FEATURE_COLUMNS]
        labels = dataset[TARGET_COLUMN].astype(int)
        class_counts = labels.value_counts()

        if class_counts.min() < 2:
            raise ValueError(
                "Each crop label needs at least two records for stratified splitting."
            )

        return train_test_split(
            features,
            labels,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=labels,
        )

    def _train_models(
        self,
        x_train: pd.DataFrame,
        x_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
    ) -> list[ModelEvaluation]:
        """Train and evaluate every configured classification algorithm."""
        evaluations: list[ModelEvaluation] = []

        for name, model in build_classifiers(self.config.random_state).items():
            LOGGER.info("Training %s.", name)
            evaluation = evaluate_classifier(
                name,
                model,
                x_train,
                x_test,
                y_train,
                y_test,
                self.config.random_state,
            )
            evaluations.append(evaluation)
            LOGGER.info("%s accuracy: %.4f", name, evaluation.accuracy)

        return evaluations

    @staticmethod
    def _select_best_model(
        evaluations: list[ModelEvaluation],
    ) -> ModelEvaluation:
        """Select by accuracy, then F1 score, cross-validation, and speed."""
        return max(
            evaluations,
            key=lambda item: (
                item.accuracy,
                item.f1_score,
                item.cross_validation_score,
                -(item.training_time_seconds + item.prediction_time_seconds),
            ),
        )

    def _save_artifacts(
        self,
        evaluations: list[ModelEvaluation],
        best_model: ModelEvaluation,
    ) -> None:
        """Persist every trained model and metadata for the selected model."""
        manager = ModelManager(self.config.models_directory)
        for evaluation in evaluations:
            manager.save_model(evaluation.name, evaluation.model)

        manager.save_best_model(best_model.model)
        manager.save_metadata(
            best_model.name,
            best_model.accuracy,
            best_model.model,
            self.config.dataset_path,
            len(FEATURE_COLUMNS),
        )

    def _write_report(self, result: TrainingResult, dataset_size: int) -> None:
        """Write a professional Markdown report for the model comparison."""
        self.config.reports_directory.mkdir(parents=True, exist_ok=True)
        report_path = self.config.reports_directory / "model_training_report.md"
        comparison_markdown = self._comparison_to_markdown(result.comparison_table)
        best = result.best_model
        report = f"""# AgriSmart AI Model Training Report

## Dataset

- Dataset: `{self.config.dataset_path.name}`
- Processed records: {dataset_size}
- Features: {', '.join(FEATURE_COLUMNS)}
- Target: `{TARGET_COLUMN}`
- Train/test split: 80% / 20% (random state {self.config.random_state})

## Algorithms Tested

- Decision Tree
- Random Forest
- Logistic Regression
- K-Nearest Neighbours
- Support Vector Machine
- Naive Bayes

## Results

{comparison_markdown}

## Best Model

- Best overall: **{best.name}**
- Accuracy: **{best.accuracy:.4f}**
- Highest accuracy model: {result.highest_accuracy_model.name}
- Fastest model: {result.fastest_model.name}

## Reason for Selection

The best model is selected by highest test accuracy. Ties are resolved using
weighted F1 score, mean cross-validation accuracy, and then lower total
training and prediction time.

## Recommendations

- Validate the selected model with new field data before deployment.
- Keep the saved scaler and label encoder with the selected model artifact.
- Monitor accuracy and retrain when the crop dataset or growing conditions change.
- Review per-model confusion matrices before exposing predictions to users.
"""
        report_path.write_text(report, encoding="utf-8")

    def _save_evaluation_details(
        self,
        evaluations: list[ModelEvaluation],
    ) -> None:
        """Save full per-model metrics, matrices, and classification reports."""
        self.config.reports_directory.mkdir(parents=True, exist_ok=True)
        details = {
            evaluation.name: {
                "accuracy": evaluation.accuracy,
                "precision": evaluation.precision,
                "recall": evaluation.recall,
                "f1_score": evaluation.f1_score,
                "cross_validation_score": evaluation.cross_validation_score,
                "training_time_seconds": evaluation.training_time_seconds,
                "prediction_time_seconds": evaluation.prediction_time_seconds,
                "confusion_matrix": evaluation.confusion_matrix,
                "classification_report": evaluation.classification_report,
            }
            for evaluation in evaluations
        }
        details_path = self.config.reports_directory / "model_evaluation_details.json"
        details_path.write_text(
            json.dumps(details, indent=2, default=float),
            encoding="utf-8",
        )

    @staticmethod
    def _comparison_to_markdown(comparison_table: pd.DataFrame) -> str:
        """Convert a comparison table to Markdown without extra dependencies."""
        headers = comparison_table.columns.tolist()
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join("---" for _ in headers) + " |"
        rows = []

        for _, row in comparison_table.iterrows():
            values = []
            for value in row:
                formatted_value = (
                    f"{value:.4f}" if isinstance(value, float) else str(value)
                )
                values.append(formatted_value)
            rows.append("| " + " | ".join(values) + " |")

        return "\n".join([header_line, separator_line, *rows])


def configure_training_logging(reports_directory: Path) -> None:
    """Configure a file logger for reproducible training records."""
    reports_directory.mkdir(parents=True, exist_ok=True)
    log_path = reports_directory / "model_training.log"

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
    """Run the model training pipeline from the command line."""
    parser = argparse.ArgumentParser(
        description="Train and compare crop recommendation classifiers."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    configuration = TrainingConfig(dataset_path=arguments.dataset)

    try:
        CropModelTrainingPipeline(configuration).run()
    except (FileNotFoundError, ValueError, OSError) as error:
        LOGGER.error("Model training could not be completed: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

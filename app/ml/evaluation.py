"""Model evaluation, comparison, and visualization helpers."""

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import matplotlib

# A non-interactive backend supports training in terminals and deployment jobs.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.base import ClassifierMixin, clone
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score


@dataclass
class ModelEvaluation:
    """Metrics, timings, and predictions from one trained classifier."""

    name: str
    model: ClassifierMixin
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    cross_validation_score: float
    training_time_seconds: float
    prediction_time_seconds: float
    confusion_matrix: list[list[int]]
    classification_report: dict


def evaluate_classifier(
    name: str,
    model: ClassifierMixin,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    random_state: int,
) -> ModelEvaluation:
    """Fit one classifier and calculate consistent evaluation metrics."""
    training_start = perf_counter()
    model.fit(x_train, y_train)
    training_time = perf_counter() - training_start

    prediction_start = perf_counter()
    predictions = model.predict(x_test)
    prediction_time = perf_counter() - prediction_start

    cross_validation_score = _calculate_cross_validation_score(
        model,
        x_train,
        y_train,
        random_state,
    )
    matrix = confusion_matrix(y_test, predictions)

    return ModelEvaluation(
        name=name,
        model=model,
        accuracy=accuracy_score(y_test, predictions),
        precision=precision_score(
            y_test,
            predictions,
            average="weighted",
            zero_division=0,
        ),
        recall=recall_score(
            y_test,
            predictions,
            average="weighted",
            zero_division=0,
        ),
        f1_score=f1_score(
            y_test,
            predictions,
            average="weighted",
            zero_division=0,
        ),
        cross_validation_score=cross_validation_score,
        training_time_seconds=training_time,
        prediction_time_seconds=prediction_time,
        confusion_matrix=matrix.tolist(),
        classification_report=classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
    )


def create_comparison_table(
    evaluations: list[ModelEvaluation],
) -> pd.DataFrame:
    """Create an accuracy-ranked comparison table for evaluated classifiers."""
    rows = [
        {
            "Model": evaluation.name,
            "Accuracy": evaluation.accuracy,
            "Precision": evaluation.precision,
            "Recall": evaluation.recall,
            "F1 Score": evaluation.f1_score,
            "Cross Validation": evaluation.cross_validation_score,
            "Training Time (s)": evaluation.training_time_seconds,
            "Prediction Time (s)": evaluation.prediction_time_seconds,
        }
        for evaluation in evaluations
    ]
    comparison = pd.DataFrame(rows)
    comparison = comparison.sort_values(
        by=["Accuracy", "F1 Score", "Cross Validation", "Training Time (s)"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    comparison.insert(0, "Rank", comparison.index + 1)
    return comparison


def save_evaluation_charts(
    evaluations: list[ModelEvaluation],
    feature_names: list[str],
    x_test: pd.DataFrame,
    y_test: pd.Series,
    best_evaluation: ModelEvaluation,
    charts_directory: Path,
    random_state: int,
) -> None:
    """Save comparison, confusion-matrix, and feature-importance charts."""
    charts_directory.mkdir(parents=True, exist_ok=True)
    _configure_plot_style()
    _save_comparison_chart(
        evaluations,
        metric_name="accuracy",
        title="Model Accuracy Comparison",
        output_path=charts_directory / "accuracy_comparison.png",
    )
    _save_comparison_chart(
        evaluations,
        metric_name="cross_validation_score",
        title="Cross-Validation Score Comparison",
        output_path=charts_directory / "cross_validation_comparison.png",
    )

    for evaluation in evaluations:
        _save_confusion_matrix_chart(evaluation, charts_directory)

    _save_feature_importance_chart(
        best_evaluation,
        feature_names,
        x_test,
        y_test,
        charts_directory / "feature_importance.png",
        random_state,
    )


def _calculate_cross_validation_score(
    model: ClassifierMixin,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int,
) -> float:
    """Return mean stratified accuracy from up to five validation folds."""
    minimum_class_count = int(y_train.value_counts().min())
    folds = min(5, minimum_class_count)

    if folds < 2:
        raise ValueError(
            "At least two training records per crop label are required for "
            "cross-validation."
        )

    cross_validator = StratifiedKFold(
        n_splits=folds,
        shuffle=True,
        random_state=random_state,
    )
    scores = cross_val_score(
        clone(model),
        x_train,
        y_train,
        cv=cross_validator,
        scoring="accuracy",
    )
    return float(scores.mean())


def _configure_plot_style() -> None:
    """Apply a consistent visual style for training charts."""
    sns.set_theme(style="whitegrid", context="notebook")


def _save_comparison_chart(
    evaluations: list[ModelEvaluation],
    metric_name: str,
    title: str,
    output_path: Path,
) -> None:
    """Save a bar chart for one metric across all models."""
    values = [getattr(evaluation, metric_name) for evaluation in evaluations]
    names = [evaluation.name for evaluation in evaluations]
    figure, axis = plt.subplots(figsize=(12, 6))
    sns.barplot(x=names, y=values, hue=names, legend=False, ax=axis)
    axis.set_title(title)
    axis.set_ylabel("Score")
    axis.set_xlabel("Model")
    axis.set_ylim(0, 1)
    axis.tick_params(axis="x", rotation=25)
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def _save_confusion_matrix_chart(
    evaluation: ModelEvaluation,
    charts_directory: Path,
) -> None:
    """Save one labelled confusion matrix chart for a model."""
    figure, axis = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        evaluation.confusion_matrix,
        cmap="Blues",
        annot=True,
        fmt="d",
        cbar=False,
        ax=axis,
    )
    axis.set_title(f"Confusion Matrix: {evaluation.name}")
    axis.set_xlabel("Predicted Label")
    axis.set_ylabel("Actual Label")
    filename = evaluation.name.lower().replace(" ", "_")
    figure.tight_layout()
    figure.savefig(
        charts_directory / f"confusion_matrix_{filename}.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(figure)


def _save_feature_importance_chart(
    evaluation: ModelEvaluation,
    feature_names: list[str],
    x_test: pd.DataFrame,
    y_test: pd.Series,
    output_path: Path,
    random_state: int,
) -> None:
    """Save permutation feature importance for the selected best model."""
    importance = permutation_importance(
        evaluation.model,
        x_test,
        y_test,
        n_repeats=10,
        random_state=random_state,
        n_jobs=-1,
        scoring="accuracy",
    )
    importance_frame = pd.DataFrame(
        {"Feature": feature_names, "Importance": importance.importances_mean}
    ).sort_values("Importance", ascending=False)

    figure, axis = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=importance_frame,
        x="Importance",
        y="Feature",
        hue="Feature",
        legend=False,
        ax=axis,
    )
    axis.set_title(f"Feature Importance: {evaluation.name}")
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)

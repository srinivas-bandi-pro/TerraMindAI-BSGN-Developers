"""Chart-generation functions for crop dataset exploratory analysis."""

from pathlib import Path

import matplotlib

# A non-interactive backend lets reports be generated on servers and CI systems.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from app.ml.dataset_loader import FEATURE_COLUMNS, TARGET_COLUMN, numeric_features


def configure_plot_style() -> None:
    """Apply a consistent, readable style to all generated EDA charts."""
    sns.set_theme(style="whitegrid", context="notebook")


def create_class_distribution_chart(
    dataset: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save a bar chart showing the number of rows for each crop class."""
    configure_plot_style()
    class_counts = dataset[TARGET_COLUMN].value_counts(dropna=False)

    figure, axis = plt.subplots(figsize=(12, 6))
    sns.barplot(
        x=class_counts.index.astype(str),
        y=class_counts.values,
        hue=class_counts.index.astype(str),
        legend=False,
        ax=axis,
    )
    axis.set_title("Crop Class Distribution")
    axis.set_xlabel("Crop Label")
    axis.set_ylabel("Number of Records")
    axis.tick_params(axis="x", rotation=45)
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def create_feature_histograms(dataset: pd.DataFrame, output_path: Path) -> None:
    """Save histograms for every numeric crop recommendation feature."""
    configure_plot_style()
    features = numeric_features(dataset)
    figure, axes = plt.subplots(3, 3, figsize=(15, 12))

    for axis, column in zip(axes.flat, FEATURE_COLUMNS):
        sns.histplot(features[column].dropna(), bins=25, kde=True, ax=axis)
        axis.set_title(f"{column} Distribution")
        axis.set_xlabel(column)

    for axis in axes.flat[len(FEATURE_COLUMNS):]:
        axis.remove()

    figure.suptitle("Feature Distributions", y=1.02)
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def create_correlation_heatmap(dataset: pd.DataFrame, output_path: Path) -> None:
    """Save a Pearson-correlation heatmap for the numeric feature columns."""
    configure_plot_style()
    correlation = numeric_features(dataset).corr()

    figure, axis = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        correlation,
        annot=True,
        cmap="coolwarm",
        center=0,
        fmt=".2f",
        square=True,
        ax=axis,
    )
    axis.set_title("Feature Correlation Heatmap")
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def create_boxplots(dataset: pd.DataFrame, output_path: Path) -> None:
    """Save boxplots used to visually inspect feature outliers."""
    configure_plot_style()
    features = numeric_features(dataset)
    melted_features = features.melt(var_name="feature", value_name="value")

    figure, axis = plt.subplots(figsize=(14, 7))
    sns.boxplot(data=melted_features, x="feature", y="value", ax=axis)
    axis.set_title("Feature Boxplots for Outlier Inspection")
    axis.set_xlabel("Feature")
    axis.set_ylabel("Value")
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)

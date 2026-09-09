"""Train one matched 22-class crop recommendation model artifact bundle."""

import json
import pickle
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET_COLUMN = "label"
DATASET_PATH = Path("data/raw/Crop_recommendation.csv")
MODELS_DIRECTORY = Path("models")
PROCESSED_DIRECTORY = Path("data/processed")
RANDOM_STATE = 42


def save_pickle(value: object, path: Path) -> None:
    """Write one binary artifact with the standard pickle serializer."""
    with path.open("wb") as output_file:
        pickle.dump(value, output_file)


def dependency_versions() -> dict[str, str]:
    """Record the runtime packages required to load the saved model."""
    return {
        package: metadata.version(package)
        for package in ("scikit-learn", "joblib", "numpy", "pandas")
    }


def main() -> None:
    """Train, validate, and save a Random Forest and matching preprocessing assets."""
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH.resolve()}")

    dataset = pd.read_csv(DATASET_PATH)
    required_columns = [*FEATURE_COLUMNS, TARGET_COLUMN]
    missing_columns = sorted(set(required_columns) - set(dataset.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {', '.join(missing_columns)}")

    dataset = dataset.loc[:, required_columns].drop_duplicates().dropna().copy()
    features = dataset.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise")
    encoder = LabelEncoder()
    labels = encoder.fit_transform(dataset[TARGET_COLUMN].astype(str).str.strip())
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=labels,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    model = RandomForestClassifier(
        n_estimators=300,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight=None,
    )
    model.fit(x_train_scaled, y_train)
    accuracy = accuracy_score(y_test, model.predict(x_test_scaled))

    class_count = len(encoder.classes_)
    if len(model.classes_) != class_count:
        raise RuntimeError(
            f"Model class count ({len(model.classes_)}) does not match label encoder "
            f"class count ({class_count})."
        )
    if scaler.n_features_in_ != len(FEATURE_COLUMNS):
        raise RuntimeError("Scaler feature count does not match the model feature order.")

    MODELS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)
    save_pickle(model, MODELS_DIRECTORY / "best_model.pkl")
    save_pickle(scaler, PROCESSED_DIRECTORY / "scaler.pkl")
    save_pickle(encoder, PROCESSED_DIRECTORY / "label_encoder.pkl")
    model_metadata = {
        "model_name": "best_model.pkl",
        "algorithm": "Random Forest Classifier",
        "model_type": "Classification",
        "model_version": "1.0",
        "version": "1.0",
        "feature_names": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "total_features": len(FEATURE_COLUMNS),
        "target_column": TARGET_COLUMN,
        "classes": encoder.classes_.tolist(),
        "class_count": class_count,
        "total_classes": class_count,
        "accuracy": round(float(accuracy), 6),
        "training_accuracy": round(float(accuracy), 6),
        "dataset_name": DATASET_PATH.name,
        "training_date": datetime.now(timezone.utc).isoformat(),
        "framework": "scikit-learn",
        "dependencies": dependency_versions(),
    }
    (MODELS_DIRECTORY / "model_metadata.json").write_text(
        json.dumps(model_metadata, indent=2), encoding="utf-8"
    )
    print(f"algorithm=Random Forest Classifier")
    print(f"test_accuracy={accuracy:.6f}")
    print(f"classes={class_count}")
    print(f"features={len(FEATURE_COLUMNS)}")


if __name__ == "__main__":
    main()

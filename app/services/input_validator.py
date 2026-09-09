"""Input validation for crop recommendation predictions."""

from dataclasses import dataclass
from typing import Any, Mapping

from app.utils.exceptions import InputValidationError


@dataclass(frozen=True)
class PredictionInput:
    """Validated numeric input expected by the trained crop model."""

    nitrogen: float
    phosphorus: float
    potassium: float
    temperature: float
    humidity: float
    ph: float
    rainfall: float

    def as_feature_list(self) -> list[float]:
        """Return values in the same order used during preprocessing/training."""
        return [
            self.nitrogen,
            self.phosphorus,
            self.potassium,
            self.temperature,
            self.humidity,
            self.ph,
            self.rainfall,
        ]


@dataclass(frozen=True)
class FeatureRule:
    """Validation metadata for an accepted prediction input field."""

    aliases: tuple[str, ...]
    minimum: float
    maximum: float | None = None


FEATURE_RULES = {
    "nitrogen": FeatureRule(("nitrogen", "n"), minimum=0, maximum=200),
    "phosphorus": FeatureRule(("phosphorus", "p"), minimum=0, maximum=200),
    "potassium": FeatureRule(("potassium", "k"), minimum=0, maximum=200),
    "temperature": FeatureRule(("temperature",), minimum=-10, maximum=60),
    "humidity": FeatureRule(("humidity",), minimum=0, maximum=100),
    "ph": FeatureRule(("ph",), minimum=0, maximum=14),
    "rainfall": FeatureRule(("rainfall",), minimum=0, maximum=500),
}


def validate_prediction_input(payload: Mapping[str, Any]) -> PredictionInput:
    """Validate a mapping of input values and return canonical model features."""
    if not isinstance(payload, Mapping):
        raise InputValidationError({"payload": "A JSON object is required."})

    normalized_payload = {
        str(key).strip().lower(): value for key, value in payload.items()
    }
    values: dict[str, float] = {}
    errors: dict[str, str] = {}

    for field_name, rule in FEATURE_RULES.items():
        raw_value = _find_value(normalized_payload, rule.aliases)

        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            errors[field_name] = "This field is required."
            continue

        if isinstance(raw_value, bool):
            errors[field_name] = "A numeric value is required."
            continue

        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            errors[field_name] = "A numeric value is required."
            continue

        if not _is_finite(numeric_value):
            errors[field_name] = "The value must be finite."
        elif numeric_value < rule.minimum:
            errors[field_name] = f"The value must be at least {rule.minimum}."
        elif rule.maximum is not None and numeric_value > rule.maximum:
            errors[field_name] = f"The value must be at most {rule.maximum}."
        else:
            values[field_name] = numeric_value

    if errors:
        raise InputValidationError(errors)

    return PredictionInput(**values)


def _find_value(payload: Mapping[str, Any], aliases: tuple[str, ...]) -> Any:
    """Return the first supplied value from a field's accepted aliases."""
    for alias in aliases:
        if alias in payload:
            return payload[alias]
    return None


def _is_finite(value: float) -> bool:
    """Return whether a float is finite without accepting NaN or infinity."""
    return value != float("inf") and value != float("-inf") and value == value

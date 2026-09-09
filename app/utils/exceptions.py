"""Domain exceptions used by AgriSmart AI backend services."""


class AgriSmartError(Exception):
    """Base exception for clean, user-safe service errors."""


class InputValidationError(AgriSmartError):
    """Raised when crop prediction input is missing or invalid."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Invalid prediction input.")
        self.errors = errors


class ModelLoadError(AgriSmartError):
    """Raised when trained model artifacts cannot be loaded safely."""


class ModelUnavailableError(AgriSmartError):
    """Raised when a prediction is requested without loaded model artifacts."""


class PredictionPersistenceError(AgriSmartError):
    """Raised when a successful prediction cannot be saved to the database."""

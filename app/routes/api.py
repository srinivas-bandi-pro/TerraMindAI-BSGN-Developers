"""JSON API endpoints for prediction, model status, and history."""

import logging
from math import ceil
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.models.database import db
from app.services.history_service import PredictionHistoryService
from app.services.model_loader import ModelLoader
from app.services.model_upload_service import ModelUploadError, ModelUploadService
from app.services.prediction_service import PredictionService
from app.services.chat_assistant import (
    ChatConfigurationError,
    ChatResponseError,
    DISEASES,
    FARMING_TIPS,
    FERTILIZERS,
    LLMChatAssistant,
    PLANTING_CALENDAR,
)
from app.utils.decorators import admin_required
from app.utils.exceptions import ModelLoadError
from app.utils.exceptions import PredictionPersistenceError


LOGGER = logging.getLogger(__name__)
api_blueprint = Blueprint("api", __name__, url_prefix="/api")
history_service = PredictionHistoryService()


@api_blueprint.post("/chat")
def chat():
    """Generate a contextual LLM answer from the user's private browser history."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
        return _json_error(400, "invalid_message", "A JSON message string is required.")
    history = payload.get("history", [])
    memory = payload.get("memory", {})
    if not isinstance(history, list) or not isinstance(memory, dict):
        return _json_error(400, "invalid_context", "History must be a list and memory must be an object.")

    assistant = LLMChatAssistant(
        current_app.config["OPENAI_API_KEY"], current_app.config["OPENAI_CHAT_MODEL"]
    )
    try:
        reply = assistant.respond(payload["message"].strip(), history, memory)
    except ChatConfigurationError:
        return _json_error(503, "ai_unavailable", "The AI assistant is not configured. Set OPENAI_API_KEY to enable it.")
    except ChatResponseError as error:
        return _json_error(503, "ai_unavailable", str(error))

    response_data: dict[str, Any] = {
        "success": True, "intent": reply.intent, "language": reply.language,
        "reply": reply.reply, "memory": reply.memory,
    }
    if reply.recommendation_inputs:
        result = current_app.extensions["prediction_service"].predict_safe(reply.recommendation_inputs)
        if result["success"]:
            recommendation = result["data"]
            response_data["recommendation"] = {
                "crop": recommendation["predicted_crop"],
                "confidence": round(recommendation["confidence"] * 100, 2),
            }
    return jsonify(response_data)


@api_blueprint.post("/recommend")
def chatbot_recommendation():
    """Return a model-based crop recommendation for the chat widget.

    This convenience endpoint accepts the same seven ML features as /predict.
    """
    if not request.is_json or not isinstance(request.get_json(silent=True), dict):
        return _json_error(400, "invalid_json", "Request content must be a JSON object.")
    result = current_app.extensions["prediction_service"].predict_safe(request.get_json())
    if not result["success"]:
        return jsonify(result), 422
    recommendation = result["data"]
    return jsonify({"success": True, "crop": recommendation["predicted_crop"], "confidence": round(recommendation["confidence"] * 100, 2)})


@api_blueprint.get("/crop-calendar")
def crop_calendar():
    """Expose the planting calendar for clients that need structured data."""
    return jsonify({"success": True, "data": PLANTING_CALENDAR})


@api_blueprint.get("/fertilizer")
def fertilizer_advice():
    """Expose short, farmer-friendly fertilizer guidance."""
    return jsonify({"success": True, "data": FERTILIZERS})


@api_blueprint.get("/disease")
def disease_advice():
    """Expose pest and disease information in structured form."""
    return jsonify({"success": True, "data": DISEASES})


@api_blueprint.get("/tips")
def farming_tips():
    """Return a daily rotating farming tip."""
    index = __import__("datetime").date.today().toordinal() % len(FARMING_TIPS)
    return jsonify({"success": True, "tip": FARMING_TIPS[index]})


@api_blueprint.get("/weather")
def weather_advice():
    """Return safe weather-aware guidance until a provider is configured."""
    return jsonify({"success": True, "available": False, "advice": "Weather service is currently unavailable."})


@api_blueprint.get("/model")
def model_information():
    """Return metadata for the currently loaded production candidate model."""
    loader = current_app.extensions["model_loader"]

    try:
        artifacts = loader.get_artifacts()
    except Exception:
        return _json_error(
            503,
            "model_unavailable",
            "Model metadata is unavailable because the model is not loaded.",
        )

    metadata = artifacts.metadata
    return jsonify(
        {
            "success": True,
            "data": {
                "model_name": metadata.get("model_name", metadata.get("algorithm")),
                "algorithm": metadata.get("algorithm", "unknown"),
                "accuracy": metadata.get("accuracy"),
                "version": metadata.get(
                    "model_version",
                    metadata.get("version", metadata.get("dataset_version", "unknown")),
                ),
                "training_date": metadata.get(
                    "training_date",
                    metadata.get("training_timestamp"),
                ),
                "dataset_name": metadata.get("dataset_name", "unknown"),
                "feature_count": metadata.get("feature_count", 0),
                "features": [
                    "N",
                    "P",
                    "K",
                    "temperature",
                    "humidity",
                    "ph",
                    "rainfall",
                ],
            },
        }
    )


@api_blueprint.post("/model/upload")
@admin_required
def upload_model_artifacts():
    """Upload a complete model artifact set in local development only."""
    if not current_app.config["MODEL_UPLOAD_ENABLED"]:
        return _json_error(403, "upload_disabled", "Model uploads are disabled.")
    uploader = ModelUploadService(current_app.config["MODEL_PATH"], current_app.config["PROCESSED_DATA_PATH"])
    staged_upload = None
    try:
        staged_upload = uploader.stage(request.files)
        loader = ModelLoader(
            staged_upload.models_directory,
            staged_upload.processed_directory,
        )
        loader.load()
        uploader.activate(staged_upload)
    except (ModelUploadError, ModelLoadError) as error:
        current_app.logger.warning("Model upload or activation failed: %s", error)
        return _json_error(400, "model_activation_failed", str(error))
    except OSError as error:
        current_app.logger.exception("Unexpected filesystem error activating uploaded model.")
        return _json_error(500, "model_activation_failed", str(error))
    finally:
        if staged_upload is not None:
            uploader.discard(staged_upload)

    active_loader = ModelLoader(
        current_app.config["MODEL_PATH"],
        current_app.config["PROCESSED_DATA_PATH"],
    )
    try:
        active_loader.load()
    except ModelLoadError as error:
        current_app.logger.exception("Activated model could not be loaded: %s", error)
        return _json_error(500, "model_activation_failed", str(error))
    current_app.extensions["model_loader"] = active_loader
    current_app.extensions["prediction_service"] = PredictionService(active_loader)
    current_app.logger.info("Uploaded model activated successfully.")
    return jsonify({"success": True, "message": "Model activated successfully."})


@api_blueprint.post("/predict")
@login_required
def create_prediction():
    """Validate a JSON request and return one crop recommendation."""
    if not request.is_json:
        return _json_error(400, "invalid_json", "Request content must be JSON.")

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_json", "Request body must be a JSON object.")

    current_app.logger.info("Prediction request received.")
    prediction_service = current_app.extensions["prediction_service"]
    result = prediction_service.predict_safe(payload)

    if result["success"]:
        recommendation = result["data"]
        alternatives = [
            {
                "crop": alternative["crop"],
                "confidence": round(float(alternative["confidence"]) * 100, 2),
            }
            for alternative in recommendation["alternative_crops"]
        ]
        return jsonify(
            {
                "success": True,
                "prediction": recommendation["predicted_crop"],
                "confidence": round(float(recommendation["confidence"]) * 100, 2),
                "prediction_probability": recommendation["prediction_probability"],
                "alternative_predictions": alternatives,
                "prediction_timestamp": recommendation["prediction_timestamp"],
                "model_version": recommendation["model_version"],
                "algorithm": recommendation["algorithm_name"],
            }
        )

    error = result["error"]
    status_code = {
        "validation_error": 422,
        "model_unavailable": 503,
        "database_error": 500,
    }.get(error["code"], 500)
    return jsonify({"success": False, "error": error}), status_code


@api_blueprint.get("/history")
@login_required
def prediction_history():
    """Return newest-first paginated prediction history."""
    page, per_page, error_response = _pagination_arguments()
    if error_response is not None:
        return error_response

    records, total_records = history_service.get_paginated_predictions(
        page,
        per_page,
    )
    return jsonify(
        {
            "success": True,
            "data": [_serialize_prediction(record) for record in records],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_records": total_records,
                "total_pages": ceil(total_records / per_page) if total_records else 0,
            },
        }
    )


@api_blueprint.delete("/history/<int:prediction_id>")
@login_required
def delete_prediction_history(prediction_id: int):
    """Delete one prediction history record by ID."""
    try:
        was_deleted = history_service.delete_prediction(prediction_id)
    except PredictionPersistenceError as error:
        return _json_error(500, "database_error", str(error))

    if not was_deleted:
        return _json_error(404, "not_found", "Prediction history record was not found.")

    return jsonify({"success": True, "message": "Prediction deleted."})


@api_blueprint.get("/dashboard")
@login_required
def dashboard_data():
    """Return backend dashboard statistics and recent predictions."""
    summary = history_service.dashboard_summary()
    model_accuracy = _model_accuracy()
    return jsonify(
        {
            "success": True,
            "data": {
                "total_predictions": summary["total_predictions"],
                "model_accuracy": model_accuracy,
                "most_predicted_crop": summary["most_predicted_crop"],
                "predictions_today": summary["predictions_today"],
                "recent_predictions": [
                    _serialize_prediction(record)
                    for record in summary["recent_predictions"]
                ],
            },
        }
    )


@api_blueprint.get("/statistics")
@login_required
def prediction_statistics():
    """Return aggregate prediction distribution and confidence information."""
    return jsonify({"success": True, "data": history_service.statistics_summary()})


def health_status() -> tuple[Any, int]:
    """Return application, database, and cached-model health information."""
    database_ok = _database_is_available()
    model_ok, metadata = _model_is_available()
    model_version = metadata.get(
        "model_version",
        metadata.get("version", metadata.get("dataset_version", "unavailable")),
    )
    is_healthy = database_ok and model_ok
    status_code = 200 if is_healthy else 503

    return (
        jsonify(
            {
                "status": "healthy" if is_healthy else "degraded",
                "application_status": "running",
                "database_status": "available" if database_ok else "unavailable",
                "model_status": "loaded" if model_ok else "unavailable",
                "current_version": model_version,
            }
        ),
        status_code,
    )


def _database_is_available() -> bool:
    """Check database connectivity without changing database state."""
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        LOGGER.exception("Database health check failed.")
        return False


def _model_is_available() -> tuple[bool, dict[str, Any]]:
    """Return cached model availability and metadata without exposing exceptions."""
    try:
        artifacts = current_app.extensions["model_loader"].get_artifacts()
        return True, artifacts.metadata
    except Exception:
        return False, {}


def _model_accuracy() -> float | None:
    """Return model accuracy when metadata is available."""
    available, metadata = _model_is_available()
    if not available:
        return None
    accuracy = metadata.get("accuracy")
    return float(accuracy) if accuracy is not None else None


def _pagination_arguments() -> tuple[int, int, tuple[Any, int] | None]:
    """Validate pagination query arguments and return a JSON error if invalid."""
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return 0, 0, _json_error(
            400,
            "invalid_pagination",
            "Page values must be integers.",
        )

    if page < 1 or not 1 <= per_page <= 100:
        return 0, 0, _json_error(
            400,
            "invalid_pagination",
            "Page must be positive and per_page must be between 1 and 100.",
        )

    return page, per_page, None


def _serialize_prediction(record: Any) -> dict[str, Any]:
    """Serialize a prediction ORM record into a JSON-safe API response."""
    return {
        "id": record.id,
        "inputs": {
            "N": record.nitrogen,
            "P": record.phosphorus,
            "K": record.potassium,
            "temperature": record.temperature,
            "humidity": record.humidity,
            "ph": record.ph,
            "rainfall": record.rainfall,
        },
        "predicted_crop": record.predicted_crop,
        "confidence": round(record.confidence_score * 100, 2),
        "created_at": record.created_at.isoformat(),
    }


def _json_error(status_code: int, code: str, message: str):
    """Build a consistent JSON error response for API endpoints."""
    return (
        jsonify({"success": False, "error": {"code": code, "message": message}}),
        status_code,
    )

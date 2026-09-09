# AgriSmart AI API Reference

The browser pages are served by Flask and the `/api/` routes return JSON. API
responses include safe error payloads; `/api/` responses are non-cacheable and
rate-limited.

## `GET /`

Renders the HTML landing page.

Status code: `200`.

## `GET /health`

Reports application, database, and model status. It is used by the Docker health
check.

```json
{
  "status": "healthy",
  "application_status": "running",
  "database_status": "available",
  "model_status": "loaded",
  "current_version": "1.0"
}
```

Status codes: `200` when database and model are available; `503` when either is
unavailable.

## `GET /api/model`

Returns metadata for the loaded model.

```json
{
  "success": true,
  "data": {
    "model_name": "Random Forest",
    "algorithm": "Random Forest",
    "accuracy": 0.98,
    "version": "1.0",
    "training_date": "2026-01-01T00:00:00+00:00",
    "dataset_name": "processed_dataset.csv",
    "feature_count": 7,
    "features": ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
  }
}
```

Status codes: `200`, `503`.

## `POST /api/predict`

Accepts a JSON object with crop features. Both `N`/`P`/`K` and
`nitrogen`/`phosphorus`/`potassium` are accepted.

```json
{
  "N": 90,
  "P": 42,
  "K": 43,
  "temperature": 20.8,
  "humidity": 82,
  "ph": 6.5,
  "rainfall": 202
}
```

Example success response:

```json
{
  "success": true,
  "prediction": "rice",
  "confidence": 98.73,
  "prediction_probability": 0.9873,
  "alternative_predictions": [{"crop": "rice", "confidence": 98.73}],
  "prediction_timestamp": "2026-01-01T00:00:00+00:00",
  "model_version": "1.0",
  "algorithm": "Random Forest"
}
```

Status codes: `200`, `400` for invalid JSON, `422` for invalid field values,
`503` for unavailable artifacts, `500` for persistence or unexpected errors.

## `GET /api/dashboard`

Returns total predictions, model accuracy, most predicted crop, today’s count, and
recent predictions.

Status codes: `200`, `500`.

## `GET /api/statistics`

Returns crop distribution, average confidence, and prediction count.

Status codes: `200`, `500`.

## `GET /api/history`

Returns newest-first history. Optional parameters: `page` (default `1`) and
`per_page` (default `20`, maximum `100`).

```json
{
  "success": true,
  "data": [{"id": 1, "predicted_crop": "rice", "confidence": 98.73}],
  "pagination": {"page": 1, "per_page": 20, "total_records": 1, "total_pages": 1}
}
```

Status codes: `200`, `400`.

## `DELETE /api/history/<id>`

Deletes one saved prediction record.

```json
{"success": true, "message": "Prediction deleted."}
```

Status codes: `200`, `404`, `500`.

## Error Format

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Optional general error message",
    "fields": {"humidity": "The value must be at most 100."}
  }
}
```

Possible status codes include `400`, `404`, `422`, `429`, `500`, and `503`.

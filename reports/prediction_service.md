# Prediction Service Architecture

## Overview

The prediction service is a backend-only component. It validates input,
reuses model artifacts loaded at application startup, performs compatible
feature scaling and label decoding, then stores each successful prediction.

## Workflow

1. Flask startup creates one `ModelLoader` and attempts to load the trained
   model, scaler, label encoder, and metadata once.
2. `PredictionService` validates every required feature and its physical range.
3. The input is converted to the training feature order and transformed by the
   persisted scaler.
4. The model predicts an encoded crop label. The persisted label encoder
   converts it back to a crop name.
5. Native model probabilities are used when available. For score-only models,
   decision scores are normalized to rank the top three crop recommendations.
6. The successful prediction is saved to SQLite through `PredictionHistoryService`.
7. The service returns a JSON-ready recommendation object.

## Validation Strategy

Inputs must include nitrogen, phosphorus, potassium, temperature, humidity,
pH, and rainfall. Values must be finite numeric values. Nitrogen, phosphorus,
potassium, and rainfall cannot be negative; humidity must be from 0 to 100;
pH must be from 0 to 14; and temperature must be from -50 to 70 degrees.

## Error Handling

- Missing or invalid fields return a `validation_error` with field messages.
- Missing or corrupted artifacts return `model_unavailable`.
- Database save failures return `database_error` and roll back the transaction.
- Unexpected failures are logged server-side and return a generic
  `prediction_error` response.

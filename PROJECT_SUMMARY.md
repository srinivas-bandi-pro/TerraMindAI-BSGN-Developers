# AgriSmart AI — Project Summary

## Overview

AgriSmart AI is an intelligent crop recommendation system using machine learning.
It accepts soil and climate measurements, validates them, applies saved model
artifacts, and presents a recommended crop with confidence information. The project
also provides history, analytics, model information, an accessible responsive
frontend, JSON APIs, and Docker-based deployment support.

## Problem and Solution

Selecting a crop involves interpreting nutrient levels, climate, pH, humidity, and
rainfall together. AgriSmart AI offers a consistent, data-informed workflow that
turns those measurements into an explainable recommendation. It is designed as a
decision-support and learning tool, not a replacement for local agricultural advice.

## Architecture

```text
Browser UI
  -> Flask HTML routes and static assets
  -> JavaScript fetch calls to /api/*
  -> PredictionService validates and prepares seven features
  -> ModelLoader reuses model, scaler, label encoder, and metadata
  -> SQLite stores prediction history
  -> Dashboard/history APIs return persisted summaries
```

The application factory configures logging, SQLAlchemy, CORS, rate limiting,
security headers, error handling, blueprints, and a reusable prediction service.

## Main Capabilities

- Crop prediction with field-level validation and structured API responses
- Prediction confidence and alternative recommendation information
- SQLite-backed prediction history with filtering and deletion
- Analytics dashboard with Chart.js charts and empty/error states
- Model metadata and health status
- About and Contact pages, including a frontend-only validated contact form
- Responsive layout, theme preference, keyboard navigation, focus states, and toasts
- Docker, Compose, Gunicorn, logs, health checks, and deployment documentation

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | HTML5, CSS3, JavaScript, Chart.js, responsive design system |
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-CORS |
| Machine learning | Scikit-learn, Pandas, NumPy, saved model artifacts |
| Database | SQLite with SQLAlchemy |
| Deployment | Docker, Docker Compose, Gunicorn |
| Quality | unittest coverage, static JavaScript checks, documented QA report |

## Documentation Map

- [README.md](README.md) — repository overview, setup, features, and API index
- [docs/API.md](docs/API.md) — API contract and examples
- [reports/testing_report.md](reports/testing_report.md) — QA coverage and findings
- [DEPLOYMENT.md](DEPLOYMENT.md) — local, Docker, logging, and cloud deployment
- [FINAL_REPORT.md](FINAL_REPORT.md) — final review and readiness assessment

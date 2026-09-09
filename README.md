# TerraMind AI

## TerraMind AI Assistant

Every TerraMind page includes the floating **TerraMind AI Assistant**. It is an
LLM-powered, agriculture-only assistant that understands English, Telugu, Roman
Telugu, and mixed-language questions. It classifies intent semantically and
uses the browser's locally stored conversation history and extracted farm facts
to handle natural follow-up questions without writing chat content to the
database.

To enable the assistant, install dependencies and set `OPENAI_API_KEY` in your
environment (see `.env.example`). The default model is `gpt-5.6-sol`; override
it with `OPENAI_CHAT_MODEL` when needed. Without a key, `/api/chat` returns a
clear `503 ai_unavailable` response rather than falling back to keyword rules.

The widget calls these public JSON endpoints:

- `POST /api/chat` — `{ "message": "When should I plant rice?", "language": "en" }`
- `POST /api/recommend` — ML feature values (`N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`)
- `GET /api/weather`, `/api/crop-calendar`, `/api/fertilizer`, `/api/disease`, `/api/tips`

Live weather needs a provider integration; until one is configured the weather
endpoint deliberately returns safe, general farming advice rather than invented
conditions.

## Intelligent Crop Recommendation System Using Machine Learning

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](#technology-stack)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](#technology-stack)
[![Scikit-learn](https://img.shields.io/badge/scikit--learn-1.6-F7931E?logo=scikitlearn&logoColor=white)](#technology-stack)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap&logoColor=white)](#technology-stack)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](DEPLOYMENT.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

TerraMind AI is an AI-Powered Intelligent Crop Recommendation System that turns soil and
climate measurements into data-informed crop suggestions. It combines a Flask
application, trained Scikit-learn artifacts, SQLite prediction history, analytics,
and a responsive frontend into one practical agricultural decision-support tool.

> This repository is structured for academic submission, portfolio presentation,
> local development, and Docker-based deployment.

## Project Overview

### Purpose

Help growers and agricultural learners interpret field conditions and make more
informed crop-planning decisions.

### Problem Statement

Crop selection depends on interacting nutrient, weather, and soil conditions.
Evaluating those inputs consistently can be difficult without a clear,
data-supported workflow.

### Solution

TerraMind AI validates seven field inputs, applies the trained prediction pipeline,
and presents a recommended crop with confidence, alternatives, history, and
analytics. It is a decision-support tool and should be used alongside local
agricultural expertise.

### Key Features

- Machine-learning crop recommendations from soil and climate data
- Client- and server-side input validation with clear error feedback
- Prediction result details and alternative crop suggestions
- Analytics dashboard, prediction history, and model information views
- Responsive, accessible user interface with theme and navigation controls
- JSON REST API with health checks, validation, rate limiting, and safe errors
- Docker, Docker Compose, Gunicorn, and production logging support

## Screenshots

Screenshots can be added to `docs/screenshots/` when preparing a submission or
portfolio. Replace each placeholder below with the matching captured image.

| View | Placeholder |
| --- | --- |
| Home Page | `docs/screenshots/home-page.png` |
| Prediction Page | `docs/screenshots/prediction-page.png` |
| Prediction Result | `docs/screenshots/prediction-result.png` |
| Analytics Dashboard | `docs/screenshots/analytics-dashboard.png` |
| Prediction History | `docs/screenshots/prediction-history.png` |
| Model Information | `docs/screenshots/model-information.png` |
| About Page | `docs/screenshots/about-page.png` |

## Technology Stack

| Area | Technologies |
| --- | --- |
| Frontend | HTML5, CSS3, JavaScript, responsive custom design system, Bootstrap 5-compatible conventions |
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-CORS |
| Machine Learning | Scikit-learn, Pandas, NumPy, trained Random Forest candidate artifacts |
| Database | SQLite and SQLAlchemy |
| Charts | Chart.js |
| Deployment | Docker, Docker Compose, Gunicorn |

## Folder Structure

```text
agrismart-ai/
|-- app/                       # Flask package: routes, services, models, utilities
|   |-- ml/                    # Dataset, preprocessing, training, evaluation modules
|   |-- models/                # SQLAlchemy data models
|   |-- routes/                # HTML and JSON route blueprints
|   |-- services/              # Prediction, model loading, history, validation
|   `-- utils/                 # Logging, exceptions, rate limiting
|-- data/
|   |-- raw/                   # Source datasets (not committed)
|   `-- processed/             # Scaler and label-encoder artifacts
|-- database/                  # Local SQLite runtime storage (not committed)
|-- docs/                      # API reference and screenshot placeholders
|-- logs/                      # Runtime logs (not committed)
|-- models/                    # Trained model artifacts (not committed)
|-- reports/                   # Evaluation and testing reports
|-- static/                    # CSS and JavaScript assets
|-- templates/                 # Jinja HTML pages and shared components
|-- tests/                     # API, service, and frontend-contract tests
|-- .env.example               # Safe environment variable template
|-- Dockerfile                 # Python 3.12 production image
|-- docker-compose.yml         # Local production-like service definition
|-- gunicorn.conf.py           # Production WSGI settings
|-- DEPLOYMENT.md              # Docker and cloud deployment guide
`-- requirements.txt           # Python dependencies
```

## Installation Guide

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/agrismart-ai.git
cd agrismart-ai
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install requirements

```bash
pip install -r requirements.txt
```

### 4. Configure environment values

Copy the template for Docker Compose or as a record of your local settings:

```bash
cp .env.example .env
```

For a direct local Flask run, export at least `FLASK_ENV=development`. A local
development secret is supplied only in development mode. For production, export a
strong `SECRET_KEY` and use `FLASK_ENV=production`. See [DEPLOYMENT.md](DEPLOYMENT.md)
for every available variable and PowerShell examples.

### 5. Provide model artifacts

Before predictions can run, make sure these generated artifacts exist:

```text
models/best_model.pkl
models/model_metadata.json
data/processed/label_encoder.pkl
data/processed/scaler.pkl
```

### 6. Run the application

```bash
python main.py
```

On Windows, after completing the setup above, you can also launch it directly
from Terminal with:

```powershell
.\run.bat
```

Open `http://127.0.0.1:5000`.

### Uploading a trained model

For local development, open `http://127.0.0.1:5000/model-upload` and use the
**Upload Model** menu item. Select these four files from the same training run:

```text
best_model.pkl
model_metadata.json
label_encoder.pkl
scaler.pkl
```

The application stores them in the correct project folders and activates the
new model. Only upload model files you trust. This feature is deliberately
disabled when `FLASK_ENV=production`.

### Docker

```bash
docker compose up --build -d
```

Set `SECRET_KEY` and `CORS_ORIGINS` in `.env` first. Full Docker, Gunicorn, logs,
health-check, and cloud instructions are available in [DEPLOYMENT.md](DEPLOYMENT.md).

## API Documentation

All `/api/` endpoints return JSON. Full request/response examples and error details
are available in [docs/API.md](docs/API.md).

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Render the landing page |
| `GET` | `/health` | Report database and model health |
| `GET` | `/api/model` | Return loaded model metadata |
| `POST` | `/api/predict` | Validate inputs and create a crop prediction |
| `GET` | `/api/dashboard` | Return dashboard summary data |
| `GET` | `/api/statistics` | Return prediction aggregates |
| `GET` | `/api/history` | Return paginated prediction history |
| `DELETE` | `/api/history/<id>` | Delete a saved prediction |

## Machine Learning Workflow

1. **Dataset** — The crop recommendation dataset contains `N`, `P`, `K`,
   temperature, humidity, pH, rainfall, and crop label values.
2. **Preprocessing** — The pipeline validates data, handles numeric gaps, reports
   outliers, scales features, and encodes labels.
3. **Training** — Candidate classifiers are evaluated and the best model artifact
   is saved alongside metadata.
4. **Evaluation** — Reports and visual outputs are generated in `reports/` for
   review before selecting a model.
5. **Prediction** — Flask loads the trained model, scaler, and label encoder once;
   validated requests are transformed and persisted to history.

Commands for dataset analysis, preprocessing, and training are documented in the
module docstrings and [DEPLOYMENT.md](DEPLOYMENT.md). Training is not required to
use an already prepared deployment.

## Features

- Responsive UI for desktop, laptop, tablet, and mobile layouts
- Crop prediction engine with validation and confidence information
- Analytics dashboard with Chart.js visualizations
- Searchable, filterable prediction history
- Model information, health status, and interface settings
- REST API with structured error responses
- About and contact pages with frontend-only contact validation
- Docker and Gunicorn production deployment support

## Future Enhancements

- User authentication and role-based access
- Weather API integration
- Satellite and remote-sensing data support
- Multi-language user interface
- Managed cloud database support
- Companion mobile application

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before opening an issue or pull request.

## Security

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Do not
open public issues containing secrets, model artifacts, or security details.

## License

This project is licensed under the [MIT License](LICENSE).

## Author

**Author:** Placeholder

**Institution / Organization:** Placeholder

**Contact:** Placeholder

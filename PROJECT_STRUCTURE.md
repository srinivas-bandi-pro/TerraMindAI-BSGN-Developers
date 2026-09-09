# AgriSmart AI — Project Structure

```text
MachineLearing/
|-- app/
|   |-- ml/                       # Data, preprocessing, training, evaluation
|   |-- models/                   # SQLAlchemy database models
|   |-- routes/                   # Main HTML and JSON API blueprints
|   |-- services/                 # Prediction, history, model-loading logic
|   `-- utils/                    # Exceptions, logging, rate limiting
|-- data/
|   |-- raw/                      # Input datasets, excluded from source control
|   `-- processed/                # Generated scaler and label encoder artifacts
|-- database/                     # Runtime SQLite storage, excluded from Git
|-- docs/
|   |-- API.md                    # API contract
|   `-- screenshots/              # Portfolio screenshot placeholders
|-- logs/                         # Runtime logs, excluded from Git
|-- models/                       # Generated model artifacts, excluded from Git
|-- reports/                      # Testing and ML reports
|-- static/
|   |-- css/                      # Shared and page-specific styles
|   `-- js/                       # Shared and page-specific browser behavior
|-- templates/
|   |-- components/               # Navbar, sidebar, footer, alerts, loader
|   `-- *.html                    # Jinja page templates
|-- tests/                        # Unit, API, and frontend contract tests
|-- .env.example                  # Safe production variable template
|-- .dockerignore                 # Lean Docker build context
|-- .gitignore                    # Runtime, secrets, tooling exclusions
|-- app.py                        # Flask development entry point
|-- config.py                     # Environment-aware app configuration
|-- Dockerfile                    # Python 3.12 production image
|-- docker-compose.yml            # Local production-like deployment
|-- gunicorn.conf.py              # Gunicorn worker and logging settings
|-- requirements.txt              # Runtime dependencies
|-- README.md                     # GitHub entry point
`-- DEPLOYMENT.md                 # Production and cloud deployment guide
```

## Organisation Notes

- Application behavior is separated from templates and static assets.
- Generated databases, logs, secrets, trained models, and raw datasets are ignored
  to keep the repository safe and reviewable.
- The model loader expects artifacts in `models/` and `data/processed/` by default;
  paths can be configured with environment variables.
- Documentation is kept at the repository root for project governance and in
  `docs/`/`reports/` for technical references and generated reports. 

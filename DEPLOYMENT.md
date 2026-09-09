# Deploying AgriSmart AI

## Requirements

- Docker Engine 24+ and Docker Compose v2 for containers, or Python 3.12 for a
  local virtual-environment deployment.
- The trained artifacts required by the application:
  `models/best_model.pkl`, `models/model_metadata.json`,
  `data/processed/label_encoder.pkl`, and `data/processed/scaler.pkl`.
- A long, random `SECRET_KEY` for production.

The application serves static files from `static/` and templates from `templates/`
inside the container. They are copied during the Docker build; no separate asset
build step is required.

## Environment Variables

Copy `.env.example` to `.env` for Docker Compose and replace placeholder values.
Do not commit the populated file.

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes, production | Long random Flask secret. |
| `FLASK_ENV` | Yes | Use `production` for deployment; this disables Flask debug mode. |
| `DATABASE_URL` | Yes | SQLAlchemy database URL. Compose defaults to persistent SQLite storage. |
| `MODEL_PATH` | Yes | Directory containing `best_model.pkl` and `model_metadata.json`. |
| `LOG_LEVEL` | Yes | Python and Gunicorn severity level, such as `INFO` or `WARNING`. |
| `PORT` | Yes | HTTP port listened to by Gunicorn. |
| `CORS_ORIGINS` | Recommended | Comma-separated allowed origins; use the public application origin. |
| `WEB_CONCURRENCY` | Optional | Gunicorn worker count; Compose defaults to `3`. |
| `GUNICORN_THREADS` | Optional | Threads per Gunicorn worker; defaults to `2`. |
| `LOG_TO_FILE` | Optional | Enables local rotating application/error files. Keep `false` in multi-worker containers and use platform log collection. |

For a generated secret on Linux or macOS:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Local Development

Create and activate a Python virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set `FLASK_ENV=development` for local work, then start the app:

```bash
python app.py
```

Use production-mode Gunicorn locally only after setting a real `SECRET_KEY` and
ensuring the model artifacts are present:

```bash
gunicorn --config gunicorn.conf.py app:app
```

## Docker Build and Run

Build the image from the repository root:

```bash
docker build -t agrismart-ai:latest .
```

Run it with persistent SQLite storage and explicitly supplied settings:

```bash
docker run --rm -p 5000:5000 \
  -e SECRET_KEY="replace-with-a-long-random-secret" \
  -e FLASK_ENV=production \
  -e DATABASE_URL="sqlite:////app/database/agrismart.db" \
  -e MODEL_PATH=/app/models \
  -e LOG_LEVEL=INFO \
  -e PORT=5000 \
  -v agrismart_database:/app/database \
  agrismart-ai:latest
```

The image runs as a non-root user and starts Gunicorn with multiple workers,
threaded request handling, bounded worker recycling, access/error logs to stdout,
and a graceful shutdown timeout.

## Docker Compose

1. Create `.env` from `.env.example` and set a real `SECRET_KEY`.
2. Confirm the trained model artifacts are present before building.
3. Start the service:

```bash
docker compose up --build -d
```

Useful operational commands:

```bash
docker compose ps
docker compose logs -f agrismart
docker compose down
```

The `agrismart_database` named volume persists SQLite data across restarts. The
container health check calls `GET /health`; it reports healthy only when both the
database and model artifacts are available.

## Logging

In containers, application, Gunicorn access, and Gunicorn error logs go to stdout
or stderr for collection by Docker or the cloud platform. This avoids unsafe shared
file rotation across multiple worker processes.

For a single-process local deployment, set `LOG_TO_FILE=true`. The application
creates `logs/application.log` and `logs/error.log` with rotating file support.
Configure `LOG_MAX_BYTES` and `LOG_BACKUP_COUNT` if the default 5 MiB and five
backups do not suit the host.

## Security Checklist

- Keep `FLASK_ENV=production`; debug mode must remain off.
- Set a strong, private `SECRET_KEY` outside source control.
- Set `CORS_ORIGINS` to the deployed frontend origin instead of `*`.
- Serve the container behind HTTPS through a managed proxy or load balancer.
- Keep the persistent database volume backed up.
- Restrict filesystem permissions for model artifacts and database backups.
- Monitor `/health`, container restarts, and structured stdout logs.

The application already includes input validation, JSON validation, safe error
responses, rate limiting, and browser security headers. No API routes are changed
by this deployment configuration.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Container is unhealthy | Verify all four model/preprocessing artifacts exist and inspect `docker compose logs agrismart`. |
| Startup rejects configuration | Set a non-empty `SECRET_KEY` and `FLASK_ENV=production`. |
| Database is not persistent | Ensure `DATABASE_URL` points to `/app/database/...` and the Compose volume is attached. |
| Browser cannot call the API | Set `CORS_ORIGINS` to the actual HTTPS application origin. |
| Port is unavailable | Change `HOST_PORT` in `.env`, then restart Compose. |
| Logs are missing from files | Containers intentionally use stdout; use `docker compose logs` or platform log aggregation. |

## Cloud Deployment Notes

### Render

Deploy from the repository with Docker, set the environment variables in the
service dashboard, and attach a persistent disk at `/app/database`. Use a managed
database for durable multi-instance deployments. Ensure model artifacts are part of
the build context or made available through secure storage at startup.

### Railway

Use Dockerfile detection, configure the variables from the environment table, and
use the provided `PORT` rather than a fixed platform port. Prefer a managed
PostgreSQL service for persistent production data when scaling beyond one instance.

### Azure App Service

Deploy the Docker image to Azure Container Registry or App Service. Configure app
settings for all environment variables, enable log streaming, and mount Azure Files
only when SQLite is retained. Azure Database for PostgreSQL is preferred for scale.

### AWS EC2

Run Compose behind an HTTPS reverse proxy or load balancer. Store environment
values in Systems Manager Parameter Store or Secrets Manager, use an EBS-backed
database volume with backups, and ship stdout logs to CloudWatch. Use a managed
database before adding multiple EC2 instances.

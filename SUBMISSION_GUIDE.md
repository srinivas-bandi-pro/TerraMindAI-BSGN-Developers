# AgriSmart AI — Submission and Demonstration Guide

## Before Submission

1. Replace placeholder author, institution, contact, and screenshot values.
2. Confirm the required model artifacts are present locally but not committed.
3. Run the automated tests in a Python-enabled environment:

   ```bash
   python -m unittest discover -s tests -v
   ```

4. Review [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md),
   [reports/testing_report.md](reports/testing_report.md), and
   [DEPLOYMENT.md](DEPLOYMENT.md).
5. Add screenshots to `docs/screenshots/` for the final GitHub portfolio view.

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set `FLASK_ENV=development`, ensure model artifacts are available, then run:

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

## Run with Docker

1. Copy `.env.example` to `.env`.
2. Set a strong `SECRET_KEY` and a restrictive `CORS_ORIGINS` value.
3. Ensure model artifacts are present in the build context.
4. Start the project:

   ```bash
   docker compose up --build -d
   ```

5. Check service status and logs:

   ```bash
   docker compose ps
   docker compose logs -f agrismart
   ```

The health endpoint is available at `GET /health`.

## Test the APIs

Use the browser, curl, Postman, or Insomnia. Example prediction request:

```bash
curl -X POST http://127.0.0.1:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"N":90,"P":42,"K":43,"temperature":20.8,"humidity":82,"ph":6.5,"rainfall":202}'
```

Check health:

```bash
curl http://127.0.0.1:5000/health
```

See [docs/API.md](docs/API.md) for the complete endpoint list and expected errors.

## Recommended Demo Flow

1. Open the landing page and explain the agricultural decision-support problem.
2. Navigate to Crop Prediction and describe the seven validated inputs.
3. Enter a valid field profile and submit the form.
4. Explain the recommendation, confidence score, and alternatives.
5. Open Prediction History to show persistence, filters, details, and deletion.
6. Open the Analytics Dashboard to demonstrate aggregate charts and service status.
7. Open Model Information to discuss metadata, health, theme, and settings.
8. Briefly show About, Contact, responsive navigation, and the Docker files.
9. Call `/health` or `/api/model` to demonstrate the backend contract.

## Known Limitations

- Predictions depend on the availability and quality of generated artifacts.
- SQLite and the in-memory rate limiter target single-instance deployments.
- Contact validation intentionally does not send messages.
- The system supports crop recommendation only; it does not provide financial,
  irrigation, pesticide, or guaranteed yield advice.

## Future Improvements

- Authentication and role-based user accounts
- Weather and satellite data integration
- Managed database and distributed rate limiting
- Multilingual and mobile-focused user experiences
- Expanded browser-based visual regression and accessibility tests

# AgriSmart AI v1.0.0 Release Notes

**Release date:** 2026-07-27

## Features

- Machine-learning crop recommendations using soil and climate inputs.
- Flask REST API for predictions, history, dashboard data, statistics, model
  metadata, and application health.
- Responsive pages for crop prediction, results, dashboard, history, model
  information, About, and Contact.
- Prediction history with filtering, pagination, details, and deletion.
- Analytics dashboard with prediction distribution, trend, and confidence charts.
- Docker, Docker Compose, Gunicorn, persistent SQLite storage, logging, and health
  checks.

## Bug Fixes and Quality Improvements

- Added consistent client/server input validation and API error handling.
- Improved keyboard modal behavior, focus restoration, and navigation links.
- Corrected dashboard service-health reporting and removed duplicate API logs.
- Added security headers, rate-limit retry guidance, and production configuration.

## Known Limitations

- The application requires generated model and preprocessing artifacts before it
  can provide predictions or report healthy status.
- SQLite and the in-memory rate limiter are suitable for a single-instance setup;
  a shared database and distributed limiter are recommended for horizontal scale.
- Contact form validation is frontend-only and does not send email.
- Social, author, institution, address, and contact values are intentional
  placeholders until project ownership details are supplied.

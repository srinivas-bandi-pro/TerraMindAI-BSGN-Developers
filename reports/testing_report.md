# AgriSmart AI Testing and Quality Assurance Report

## Scope

This review covered Flask startup configuration, database/model integration points,
the prediction, history, dashboard, model, and health APIs, plus the shared
frontend shell, prediction workflow, dashboard, history, contact form, and
responsive design contracts. Backend APIs and the trained model were not changed.

## Automated Test Coverage

| Area | Coverage |
| --- | --- |
| Prediction service | Valid recommendation, missing fields, invalid numeric input, negative values, extreme values, unavailable model |
| Prediction API | Successful response, validation response, non-JSON payload |
| History API | Pagination, deletion, invalid pagination, missing record |
| Dashboard and statistics API | Summary and aggregate response |
| Model and health APIs | Loaded model metadata and health response |
| Public pages | Landing, About, Contact, Prediction, Dashboard, and History render contracts |
| Frontend validation | Required form hooks, numeric boundaries, inline feedback, contact counter/reset/toast contract |
| Security headers | Cache prevention and browser safety headers on API responses |

The suite is located in `tests/` and uses deterministic fakes for model artifacts
and prediction responses, so it does not alter the machine-learning model.

## Verification Performed

- JavaScript syntax validation passed for every file in `static/js/` using
  `node --check`.
- Static review found no stale `about_contact.css` reference and no disabled
  navigation items that link to `#`.
- Line-length review was performed for changed Python modules; changed code follows
  the project's PEP 8 line-length standard.
- Flask/unit tests were not executable in this environment because the installed
  Python launcher reports that no Python interpreter is available. Run
  `python -m unittest discover -s tests -v` in the project virtual environment.

## Bugs Found and Fixed

1. API requests were logged twice: once application-wide and once by the API
   blueprint. The duplicate blueprint logger was removed.
2. Analytics and settings navigation entries were styled as unavailable links but
   still navigated to `#`. They now point to the existing Dashboard and Model
   Information/Settings pages.
3. Footer anchors broke when used from pages other than the landing page. They now
   link back to the landing-page sections.
4. The dashboard marked the database as healthy whenever the dashboard endpoint
   responded, rather than using the health check. It now uses `/health` for each
   service indicator.
5. Server-side nutrient and rainfall fields accepted impractically large values
   despite bounded frontend controls. Backend validation now matches the form's
   safe input ranges.
6. Modal dialogs did not consistently restore focus or trap keyboard focus. Shared
   modal handling now restores focus, supports Escape, and keeps Tab navigation
   within an open dialog.

## Performance Improvements

- Chart.js and the dashboard script now use `defer`, preventing parser blocking.
- Dashboard fetches are normalized through a shared JSON helper and chart instances
  are destroyed before refresh, preventing duplicate canvas allocations.
- Dashboard table rendering uses DOM nodes rather than HTML string interpolation
  for API-derived values.
- Duplicate API logging was removed to reduce unnecessary I/O.

## Accessibility Improvements

- Modal dialogs now support Escape, focus trapping, and focus restoration.
- Navigation no longer exposes links falsely marked as disabled.
- Existing inline validation, `aria-describedby`, live error regions, visible focus
  styling, semantic tables, and labelled controls were retained and covered by
  regression tests.

## Security Review

- API payloads are validated as JSON objects before prediction handling.
- Numeric input rejects missing, non-finite, boolean, negative, and out-of-range
  values before model inference.
- API responses are non-cacheable and use `nosniff` protection.
- Added `Content-Security-Policy`, `X-Frame-Options`, `Referrer-Policy`, and
  `Permissions-Policy` response headers.
- Rate-limited API responses now include `Retry-After` guidance.
- Dynamic dashboard/table values are inserted with `textContent`, mitigating DOM
  XSS from unexpected API data.
- The application does not use cookie-authenticated state-changing requests, so
  CSRF tokens are not currently applicable. Add CSRF protection before introducing
  sessions, accounts, or cookie-authenticated mutations.

## Recommendations Before Deployment

1. Configure `SECRET_KEY`, `CORS_ORIGINS`, and a production WSGI server through
   environment variables; never deploy with development configuration.
2. Run the test suite in CI with a supported Python environment and add browser
   integration tests (Playwright or Selenium) for viewport-specific visual checks.
3. Replace placeholder social/contact values and consider self-hosting third-party
   fonts and Chart.js for stricter supply-chain control.
4. Move the in-memory rate limiter to shared storage if the application is deployed
   on multiple worker processes or hosts.

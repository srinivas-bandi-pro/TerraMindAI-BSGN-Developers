# Security Policy

## Supported Version

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| Earlier versions | No |

## Reporting a Vulnerability

Please do not report security vulnerabilities through a public GitHub issue.
Instead, contact the project maintainer or institution placeholder privately with:

- a concise description of the issue;
- affected file, endpoint, or deployment component;
- reproduction steps or proof of concept;
- potential impact; and
- suggested mitigation, if known.

Allow reasonable time for acknowledgement and remediation before public disclosure.
Do not include credentials, private datasets, or production data in the report.

## Security Practices

AgriSmart AI includes input validation, safe JSON error responses, rate limiting,
security headers, and production environment-variable configuration. Deployers are
responsible for using a strong `SECRET_KEY`, restrictive `CORS_ORIGINS`, HTTPS,
private model/database storage, and supported dependency versions.

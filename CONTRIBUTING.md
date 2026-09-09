# Contributing to AgriSmart AI

Thank you for your interest in improving AgriSmart AI. Contributions should keep
the project clear, accessible, secure, and suitable for agricultural
decision-support learning.

## Before You Start

- Read the [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md).
- Search existing issues before opening a new one.
- Do not commit datasets with restricted terms, trained artifacts, local databases,
  `.env` files, logs, or credentials.
- Discuss substantial user-interface, API, or machine-learning changes in an issue
  before implementation.

## Development Workflow

1. Fork the repository and create a focused branch.
2. Set up a virtual environment and install `requirements.txt`.
3. Make one logical change with readable names and documentation where appropriate.
4. Run the available tests:

   ```bash
   python -m unittest discover -s tests -v
   ```

5. Verify relevant pages and responsive layouts manually.
6. Update documentation or tests when behavior changes.
7. Open a pull request using a concise title and description.

## Pull Request Checklist

- [ ] Scope is focused and does not include unrelated formatting.
- [ ] No secrets, runtime databases, logs, or generated model files are included.
- [ ] Tests are added or updated where practical.
- [ ] Existing tests pass in a supported Python environment.
- [ ] Accessibility, validation, and responsive behavior were considered.
- [ ] API and deployment documentation remains accurate.

## Commit Guidance

Use short, descriptive commits, for example:

```text
docs: clarify Docker health check requirements
fix: handle empty history response
test: cover invalid prediction payload
```

## Reporting Bugs

Describe the expected result, actual result, reproduction steps, environment, and
relevant non-sensitive logs. Report security vulnerabilities privately according
to [SECURITY.md](SECURITY.md).

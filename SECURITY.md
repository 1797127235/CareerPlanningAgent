# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue.

Email the maintainer at [liu1797127235@gmail.com](mailto:liu1797127235@gmail.com) with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact

We will respond within 48 hours and work with you to verify and address the issue.

## Data Privacy

CareerOS is designed to be **local-first**:

- Resume data, career goals, and growth logs are stored locally in SQLite (`data/app_state/app.db`)
- LLM API calls go to DashScope (Alibaba Cloud) — your API key never leaves your machine
- No data is sent to external servers without explicit user action

## Key Privacy Principles

| Principle | Implementation |
|-----------|---------------|
| Resume data stays local | SQLite database on user's machine |
| API key is user-controlled | Stored in `.env`, never committed |
| LLM calls are scoped | Only relevant data sent to LLM, not full profile |
| Evidence over fabrication | AI suggestions are traceable to actual data |
| No auto-submission | CareerOS never submits applications or modifies profiles without explicit confirmation |

## Security Best Practices for Contributors

- Never commit `.env` files or API keys
- Validate all user inputs before sending to LLM
- Keep dependencies updated (`pip list --outdated`, `npm outdated`)
- Use parameterized queries (SQLAlchemy handles this by default)

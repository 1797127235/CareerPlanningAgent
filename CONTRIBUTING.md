# Contributing to CareerOS

Welcome! CareerOS is an open-source AI career planning platform. We love receiving contributions from the community — code, docs, translations, bug reports, or ideas.

## Quick Setup

```bash
git clone https://github.com/1797127235/CareerPlanningAgent.git
cd CareerPlanningAgent
cp .env.example .env
# Add your DASHSCOPE_API_KEY to .env
python seed_demo.py              # create demo data
run.bat                          # start backend + frontend
```

## Architecture Overview

```
frontend-v2/          React SPA (Tailwind CSS + Framer Motion)
backend/              FastAPI REST API
agent/                LangGraph multi-agent orchestration
data/                 Career graph + market signals (runtime)
data-deploy/          Data templates (committed to repo)
```

Key files:
- `backend/app.py` — App factory + router registration
- `agent/supervisor.py` — Agent dispatcher
- `frontend-v2/src/pages/` — Route-level components

## Development Workflow

1. **Pick an issue** — Start with `good first issue` or `help wanted`
2. **Create a branch** — `git checkout -b feature/your-feature`
3. **Write code** — Follow existing patterns
4. **Test** — `python -m pytest -q tests` (backend) + `cd frontend-v2 && npm run build` (frontend)
5. **Commit** — Use conventional commits: `feat(module): description`
6. **Open PR** — Describe what you changed and why

## Commit Convention

```
feat(module): add something new
fix(module): fix a bug
docs: documentation changes
refactor(module): improve code structure
test: add or fix tests
chore: maintenance tasks
```

## Code Style

- Python: Follow PEP 8, use type hints
- TypeScript/React: Use existing patterns in the codebase
- Import order: `__future__` → stdlib → third-party → local

## Testing

```bash
# Run all tests
python -m pytest -q tests

# Run specific test file
python -m pytest -q tests/services/

# Frontend build check
cd frontend-v2 && npm run build
```

## Discussion

For questions about architecture or feature ideas, open a [GitHub Discussion](https://github.com/1797127235/CareerPlanningAgent/discussions).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

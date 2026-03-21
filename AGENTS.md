# Repository Guidelines

## Project Structure & Module Organization

- `src/` contains the FastAPI app:
  - `main.py` — app init, middleware, router mounts
  - `db.py` — psycopg3 connection pool (lazy-init, min=1/max=5)
  - `crud.py` — all database operations as raw SQL against Postgres
  - `deps.py` — helpers: templates, auth (admin PIN), `extract_card_id()`
  - `config.py` — settings from environment variables
  - `routers/` — kiosk, admin, reports
- `src/templates/` — Jinja2 templates
- `src/static/` — CSS, JS
- `docs/` — original requirements and flow docs (pre-migration)

## Database

This system connects to a **shared Postgres** database owned by `fgt-checkin-system`. Tables used:

- `players` — shared player table (READ only from this system)
- `card_ids` — maps card IDs to player UUIDs (READ only)
- `meetup_sessions` — meetup session lifecycle
- `meetup_checkins` — per-player/guest checkins within a session
- `meetup_headcounts` — manual head counts

**Pattern:** raw SQL with `psycopg3` + `psycopg_pool.ConnectionPool`. No ORM.
All `crud.py` functions manage their own connections from the pool.

## Build, Test, and Development Commands

- `docker compose -p fgt-meetup-dev -f docker-compose.dev.yml up --build` — run with Docker
- `pip install -r requirements.txt` — install runtime deps
- `uvicorn src.main:app --reload` — run locally (needs Postgres accessible)
- `pip install -r requirements-dev.txt && pytest` — run tests

## Coding Style & Naming Conventions

- Python: 4-space indent, `snake_case` for functions/vars, `PascalCase` for classes
- JS/CSS: 2-space indent, `camelCase` in JS, `kebab-case` for CSS classes
- SQL: UPPERCASE keywords, lowercase table/column names
- Templates: Jinja2 in `src/templates/`, static in `src/static/`

## Key Terminology

- **Player** (not "member") — a person in the `players` table
- **Card ID** — short ID like `FGC-A7K9X2` linking to a player (from membership card system)
- **Session** — a meetup event (open → closed lifecycle)
- **Checkin** — a player or guest registering attendance at a session

## Commit & Pull Request Guidelines

- Short, imperative commit messages ("Add headcount tracking", "Fix checkout logic")
- PRs: concise summary, link related issues, screenshots for UI changes
- Migration branch: `feature/postgres-migration`

## Configuration

Runtime settings from env vars: `DATABASE_URL`, `ADMIN_PIN`, `SECRET_KEY`.
Defaults in `src/config.py`. See `.env.example`.

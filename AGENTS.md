# Repository Guidelines

## Project Structure & Module Organization

- `src/` contains the FastAPI app. Key modules include `main.py` (routes), `crud.py` (database operations), `models.py` (SQLAlchemy models), `db.py` (engine/session), and `config.py` (settings). Templates live in `src/templates/` and static assets in `src/static/`.
- `docs/` holds requirements, flow docs, and wireframes.
- `data/` stores the local SQLite database and CSV exports.
- `assets/` contains branding and QR-related assets.
- `scripts/` contains helper scripts.
- `.env.example` documents expected environment variables.

## Build, Test, and Development Commands

- `python -m venv .venv` creates a virtual environment.
- `\.\.venv\Scripts\Activate.ps1` activates the venv on Windows.
- `pip install -r requirements.txt` installs runtime dependencies.
- `uvicorn src.main:app --reload` runs the app locally with auto-reload.

## Coding Style & Naming Conventions

- Python: 4-space indentation, `snake_case` for functions/vars, `PascalCase` for classes (follow `src/*.py`).
- JS/CSS: 2-space indentation, `camelCase` in JS, `kebab-case` for CSS class names.
- Templates: keep Jinja2 templates in `src/templates/` and static files in `src/static/`.

## Testing Guidelines

- No testing framework or coverage requirements are defined yet. If you add tests, prefer a `tests/` package and document the test command in `README.md`.

## Commit & Pull Request Guidelines

- No Git history is available in this workspace, so no established commit convention was found. Use short, imperative messages (for example: "Add member import validation").
- For PRs, include a concise summary, link any related issues, and add screenshots for kiosk/admin UI changes.

## Configuration & Data

- Runtime settings come from environment variables: `ADMIN_PIN`, `SECRET_KEY`, `DATABASE_URL`. Defaults are defined in `src/config.py`.
- The default database is `data/meetups.db`; avoid committing real attendee data.

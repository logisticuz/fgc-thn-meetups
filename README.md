# FGC THN Meetups

Attendance tracking for FGC Trollhattan weekly meetups.

Goals:
- QR check-in first, NFC later
- Offline-first logging with optional sync
- Exportable reports for Studieframjandet (SFR)
- Basic stats for the association

Project layout:
- docs/        Notes and requirements
- src/         FastAPI app (templates + static)
- data/        SQLite database and exports
- scripts/     Helper scripts
- assets/      Logos, QR templates, etc.

Quick start (local):
- python -m venv .venv
- .\\.venv\\Scripts\\Activate.ps1
- pip install -r requirements.txt
- uvicorn src.main:app --reload

Admin PIN is read from ADMIN_PIN in .env (see .env.example).

# FGC THN Meetups

Närvarosystem for FGC Trollhattans veckotraffar (onsdag & sondag).

Del av **FGC THN-ekosystemet** — tre system som delar en gemensam Postgres-databas:

| System | Repo | Funktion |
|--------|------|----------|
| Turneringar | `fgt-checkin-system` | Turnerings-checkin, spelarhantering, eBas-integration |
| Medlemskort | `fgt-member-card` | Digitala medlemskort med QR-kod |
| **Meetups** | `fgc-thn-meetups` | **Detta repo** — veckotraffar, narvarohantering |

## Funktioner

- **Kiosk-vy** — QR-skanning for checkin/checkout via medlemskort
- **Gast-checkin** — gastar kan checka in utan medlemskap
- **Admin-panel** — sessionshantering, manuell checkin, headcount, historik
- **Statistik** — trender per session, topp-spelare, snittdeltagare
- **CSV-export** — narvarorapporter for Studieframjandet (SFR)

## Arkitektur

```
Postgres (fgc_checkin)
  ├── players            ← delad tabell (ags av turneringssystemet)
  ├── card_ids           ← kort-ID → spelare (ags av medlemskort)
  ├── meetup_sessions    ← detta system
  ├── meetup_checkins    ← detta system
  └── meetup_headcounts  ← detta system
```

- **psycopg3 + connection pool** — raw SQL, samma monster som ovriga system
- **FastAPI** med Jinja2-templates och statiska filer
- **Docker** — ansluter till turneringssystemets natverk for att na Postgres

## Forutsattningar

- Python 3.11+
- Postgres (kors av `fgt-checkin-system` i Docker)
- Docker-natverket `fgt-dev_fgt-net` maste finnas

## Kom igang (Docker — rekommenderat)

```bash
docker compose -p fgt-meetup-dev -f docker-compose.dev.yml up --build
```

Appen kors pa `http://localhost:8004` (eller den port som konfigureras).

## Kom igang (lokal utveckling)

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

Skapa `.env` fran `.env.example`:
```bash
cp .env.example .env
```

Starta:
```bash
uvicorn src.main:app --reload
```

## Tester

```bash
pip install -r requirements-dev.txt
pytest
```

## Miljovaribler

| Variabel | Beskrivning | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Postgres-anslutning | `postgresql://fgc:devpassword@postgres:5432/fgc_checkin` |
| `ADMIN_PIN` | PIN for admin-panel | `fgcthn2016` |
| `SECRET_KEY` | Session-kryptering | `change-me` |

## Projektstruktur

```
src/
  main.py          FastAPI-app, middleware, router-mount
  db.py            psycopg3 connection pool
  crud.py          Alla databasfunktioner (raw SQL)
  deps.py          Hjalp: templates, auth, extract_card_id
  config.py        Settings fran env
  routers/
    kiosk.py       Kiosk-vy + QR-checkin API
    admin.py       Admin-panel + sessionshantering
    reports.py     Statistik + CSV-export
  templates/       Jinja2-templates
  static/          CSS + JS
```

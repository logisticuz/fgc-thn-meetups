# Arbetsorder: Migrera meetup-system till Postgres + raw SQL

**Datum:** 2026-03-21
**Syfte:** Byta meetup-systemet från SQLite + SQLAlchemy ORM till gemensam Postgres + raw SQL (psycopg3).
**Varför:** Alla tre FGC THN-system (turneringar, medlemskort, meetups) ska dela en gemensam Postgres-databas med `players` som delad spelartabell. Konsekvent mönster med raw SQL + psycopg3 connection pool.

---

## Kontext

### Ekosystemet
- **fgt-checkin-system** (turneringar) — äger Postgres, `players`-tabellen, n8n-integrationer
- **fgt-member-card** (medlemskort) — läser `players` + `card_ids`, egen FastAPI
- **fgc-thn-meetups** (detta repo) — ska migreras från SQLite till gemensam Postgres

### Befintliga tabeller i Postgres (skapade av fgt-checkin-system)
```sql
-- Redan finns:
players (uuid, name, tag, email, telephone, games_played, total_events, ...)
card_ids (card_id TEXT PK, player_uuid TEXT FK → players.uuid, created_at)
meetup_sessions (id SERIAL PK, start_time, end_time, location, status, notes, created_at)
meetup_checkins (id SERIAL PK, session_id FK, player_uuid TEXT nullable, guest_name, method, checkin_time, checkout_time, created_by)
meetup_headcounts (id SERIAL PK, session_id FK, count, recorded_at, created_by)
```

### Postgres-anslutning
```
DATABASE_URL=postgresql://fgc:devpassword@postgres:5432/fgc_checkin
```
Containern ansluter till Docker-nätverket `fgt-dev_fgt-net` (DEV).

---

## Vad som ska göras

### Steg 1: Ta bort SQLAlchemy-beroenden

**Filer att ändra:**
- `requirements.txt` / `requirements-dev.txt` — ta bort `sqlalchemy`, lägg till `psycopg[binary]`, `psycopg_pool`
- `src/models.py` — **TA BORT HELT**. Tabellerna definieras i fgt-checkin-system/db/init.sql.

### Steg 2: Ny databasanslutning (`src/db.py`)

Byt från SQLAlchemy engine/session till psycopg3 connection pool. Följ mönstret i `fgt-checkin-system/shared/postgres_api.py`:

```python
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("Missing DATABASE_URL")

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        import psycopg_pool
        _pool = psycopg_pool.ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"autocommit": True},
        )
        logger.info("Postgres connection pool initialized (meetup)")
    return _pool

def get_connection():
    return _get_pool().connection()
```

### Steg 3: Skriv om `src/crud.py` — raw SQL

Alla funktioner ska använda `_get_pool().connection()` + `cursor.execute()` istället för SQLAlchemy ORM.

**Tabellnamnsmappning:**
| Gammal (SQLAlchemy) | Ny (Postgres) |
|---------------------|---------------|
| `sessions` / `Session` | `meetup_sessions` |
| `checkins` / `Checkin` | `meetup_checkins` |
| `headcounts` / `Headcount` | `meetup_headcounts` |
| `members` / `Member` | `players` (läs) + `card_ids` (läs) |
| `import_batches` / `ImportBatch` | Behövs ej (import hanteras av turneringssystemet) |
| `audit_log` / `AuditLog` | Kan använda befintlig `audit_log` i Postgres eller skapa `meetup_audit_log` |

**Kolumnmappning Member → players:**
| Member (gammal) | players (ny) |
|-----------------|--------------|
| `id` | `uuid` (TEXT, inte INTEGER) |
| `first_name` + `last_name` | `name` (ett fält) |
| `member_number` | Finns ej — inte relevant |
| `token_hash` | `card_ids.card_id` (via JOIN) |
| `display_name` | `tag` |
| `discord_id` | Finns ej i players |
| `membership_start/end` | `is_member` (boolean) |

**Kolumnmappning Checkin → meetup_checkins:**
| Checkin (gammal) | meetup_checkins (ny) |
|------------------|---------------------|
| `member_id` (INTEGER FK) | `player_uuid` (TEXT, nullable) |
| `guest_name` | `guest_name` (oförändrad) |
| `method` | `method` (oförändrad) |
| `checkin_time` | `checkin_time` (oförändrad) |
| `checkout_time` | `checkout_time` (oförändrad) |

**Funktioner att skriva om (alla i crud.py):**

#### Sessions
```python
def get_open_session():
    # SELECT * FROM meetup_sessions WHERE status = 'open' ORDER BY start_time DESC LIMIT 1

def start_session(location, notes):
    # INSERT INTO meetup_sessions (location, notes, status) VALUES (%s, %s, 'open') RETURNING *

def end_session(session_id):
    # UPDATE meetup_sessions SET status = 'closed', end_time = NOW() WHERE id = %s

def get_all_sessions():
    # SELECT s.*, COUNT(c.id) as total_checkins FROM meetup_sessions s
    # LEFT JOIN meetup_checkins c ON c.session_id = s.id
    # GROUP BY s.id ORDER BY s.start_time DESC
```

#### Player lookups (läser från players + card_ids)
```python
def get_player_by_card_id(card_id):
    # SELECT p.* FROM players p JOIN card_ids c ON c.player_uuid = p.uuid WHERE c.card_id = %s

def search_players_by_name(query):
    # SELECT * FROM players WHERE LOWER(name) LIKE %s OR LOWER(tag) LIKE %s LIMIT 10

def link_card(player_uuid, card_id):
    # INSERT INTO card_ids (card_id, player_uuid) VALUES (%s, %s)
    # ON CONFLICT (card_id) DO NOTHING
```

#### Checkins
```python
def create_checkin(session_id, player_uuid, guest_name, method, created_by):
    # INSERT INTO meetup_checkins (...) VALUES (...) RETURNING *

def get_checkin_for_player(session_id, player_uuid):
    # SELECT * FROM meetup_checkins WHERE session_id = %s AND player_uuid = %s

def get_session_checkins(session_id):
    # SELECT c.*, p.name, p.tag FROM meetup_checkins c
    # LEFT JOIN players p ON p.uuid = c.player_uuid
    # WHERE c.session_id = %s ORDER BY c.checkin_time

def checkout_player(session_id, player_uuid):
    # UPDATE meetup_checkins SET checkout_time = NOW()
    # WHERE session_id = %s AND player_uuid = %s AND checkout_time IS NULL

def count_checkins(session_id):
    # SELECT COUNT(*) FROM meetup_checkins WHERE session_id = %s

def count_present(session_id):
    # SELECT COUNT(*) FROM meetup_checkins WHERE session_id = %s AND checkout_time IS NULL

def delete_checkin(checkin_id):
    # DELETE FROM meetup_checkins WHERE id = %s
```

#### Headcounts
```python
def create_headcount(session_id, count, created_by):
    # INSERT INTO meetup_headcounts (session_id, count, created_by) VALUES (...)

def get_session_headcounts(session_id):
    # SELECT * FROM meetup_headcounts WHERE session_id = %s ORDER BY recorded_at
```

#### Statistik
```python
def get_overview_stats():
    # Aggregera: total members, total sessions, total checkins, avg per session, most active

def get_session_stats(limit=20):
    # JOIN meetup_sessions + meetup_checkins + meetup_headcounts, GROUP BY session

def get_member_stats():
    # Aggregera per player: total sessions, last attended, avg duration

def get_member_streak(player_uuid):
    # Loop genom closed sessions, räkna consecutive attendance
```

### Steg 4: Uppdatera `src/deps.py`

- Ta bort `get_db()` som ger SQLAlchemy session
- `extract_token()` — behåll logiken men uppdatera för card_ids:
  - Extraherar card_id från QR-URL (t.ex. `https://medlemskort.fgctrollhattan.se/FGC-A7K9X2` → `FGC-A7K9X2`)
- `hash_token()` — behövs troligen inte längre (card_ids använder ren text, inte hash)
- Behåll: `is_admin()`, `require_admin()`, `normalize_header()`, `parse_date()`, `templates`

### Steg 5: Uppdatera `src/config.py`

```python
@dataclass(frozen=True)
class Settings:
    admin_pin: str = os.getenv("ADMIN_PIN", "fgcthn2016")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://fgc:devpassword@postgres:5432/fgc_checkin")
```

### Steg 6: Uppdatera `src/main.py`

- Ta bort `from .db import Base, engine` och `Base.metadata.create_all(bind=engine)`
- Importera nya db-modulen för att initiera connection pool vid startup
- Behåll allt annat (FastAPI, middleware, routers, static files)

### Steg 7: Uppdatera routers

Alla tre routers (`kiosk.py`, `admin.py`, `reports.py`):
- Ta bort `db: Session = Depends(get_db)` parametrar
- Anropa crud-funktioner direkt (de hanterar sin egen connection pool internt)
- Byt `member` → `player` i variabelnamn
- `member.first_name + " " + member.last_name` → `player["name"]`
- `member.id` → `player["uuid"]`

### Steg 8: Uppdatera templates (minimalt)

- `members.html` — byt `member.first_name`, `member.last_name` etc. till `member.name`, `member.tag`
- Övriga templates bör funka utan ändringar om CRUD returnerar dicts med samma nycklar

### Steg 9: Ta bort oanvända filer

- `src/models.py` — ta bort
- eBas CSV-importlogik i `reports.py` — kan tas bort eller behållas som legacy
- `data/meetups.db` — SQLite-filen behövs inte längre

---

## Vad som INTE ska ändras

- Templates (HTML) — minimal påverkan
- JavaScript (kiosk.js, admin.js) — API-endpointsen är samma
- Static files (styles.css) — inget ändras
- QR-skanningslogik i kiosken — funkar som förut
- Admin-panel funktionalitet — samma features, ny datakälla

---

## Testning

1. Starta DEV-stacken: `docker compose -p fgt-dev -f docker-compose.dev.yml up --build`
2. Verifiera att meetup-appen ansluter till Postgres (kolla loggar)
3. Testa: skapa session → checka in spelare (QR + manuellt + gäst) → headcount → avsluta session
4. Testa: admin-panel (historik, medlemslista, statistik)
5. Verifiera att turneringssystemets data inte påverkats

---

## Prioritetsordning

1. db.py (connection pool)
2. crud.py (alla SQL-funktioner)
3. deps.py (ta bort ORM-beroende)
4. config.py (Postgres URL)
5. main.py (ta bort create_all)
6. routers (uppdatera anrop)
7. templates (Member → Player)
8. Städa bort models.py och SQLite-filer

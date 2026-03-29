# Codex Context — fgc-thn-meetups

Senast uppdaterad: 2026-03-29

## Vad ar det har?

Narvarosystem for FGC Trollhattans veckotraffar (onsdag/sondag, 3-15 personer).
FastAPI + Jinja2 + vanilla JS. Kors i Docker.

## Ekosystem

Tre system delar en Postgres-databas (`fgc_checkin`):

| System | Repo | Port | Status |
|--------|------|------|--------|
| Turneringar | `fgt-checkin-system` | 8001 | Produktion |
| Medlemskort | `fgt-member-card` | 8003 | **Produktion** (deploy 2026-03-24) |
| **Meetups** | `fgc-thn-meetups` | 8004 | **Produktion** (deploy 2026-03-24) |

Alla tre ansluter till Docker-natverket `fgt-dev_fgt-net` for att na Postgres och n8n.

## Vad som ar GJORT (ror inte)

- [x] Migrering fran SQLAlchemy/SQLite till psycopg3/Postgres — **klar**
- [x] `src/db.py` — psycopg3 connection pool (lazy-init, min=1/max=5, autocommit=True)
- [x] `src/crud.py` — alla DB-funktioner som raw SQL mot Postgres
- [x] `src/deps.py` — ORM-fritt, `extract_token()` for card_id-extraktion
- [x] `src/config.py` — Postgres URL som default
- [x] `src/main.py` — ingen `create_all`, ingen SQLAlchemy
- [x] `src/models.py` — **raderad** (tabeller ags av turneringssystemet)
- [x] Routers (`kiosk.py`, `admin.py`, `reports.py`) — dict-baserad data, inga ORM-objekt
- [x] Templates — "Medlem" → "Spelare", "Sverok QR" → "medlemskort"
- [x] JS — `token_hash` → `card_id`, `pendingTokenHash` → `pendingCardId`
- [x] Testsvit — 31 mock-baserade tester (mockar `crud`-funktioner, **inte** SQLite)
- [x] Docker — `Dockerfile` + `docker-compose.dev.yml` + `.dockerignore`
- [x] Repo pa GitHub: `logisticuz/fgc-thn-meetups` (public)
- [x] Import-sidan borttagen fran admin-menyn (hanteras av turneringssystemet)

## Databasschema (delade tabeller — ags av fgt-checkin-system)

```sql
-- Ror INTE dessa, de skapas av turneringssystemets init.sql
players (uuid TEXT PK, name, tag, email, telephone, total_events, is_member, ...)
card_ids (card_id TEXT PK, player_uuid TEXT FK → players.uuid)
audit_log (id SERIAL, timestamp, user_name, action, target_table, details)
```

## Databasschema (meetup-tabeller — ags av detta system)

```sql
meetup_sessions (id SERIAL PK, start_time, end_time, location, notes, status, created_at)
meetup_checkins (id SERIAL PK, session_id FK, player_uuid TEXT nullable, guest_name, checkin_time, checkout_time, method, created_by)
meetup_headcounts (id SERIAL PK, session_id FK, count, recorded_at, created_by)
```

`player_uuid` ar nullable — gastar checkar in med bara `guest_name`.

## Kodmonster

- **Ingen ORM.** Raw SQL med `psycopg3`. Anslutningar fran `db.get_connection()`.
- **Alla crud-funktioner** hanterar sin egen connection: `with get_connection() as conn:`
- **Crud returnerar ra datetime.** Ingen `.isoformat()` i crud — routrarna serialiserar (FastAPI auto-serialiserar, Jinja usar `.strftime()`).
- **Dicts overallt.** Inga ORM-objekt. `_row_dict(cursor, row)` konverterar.
- **Autocommit.** Poolen skapas med `kwargs={"autocommit": True}`.
- **Timezone.** Poolen konfigurerar varje connection med `SET timezone = 'Europe/Stockholm'`.
- **Templates** anvander Jinja2 dot-notation pa dicts (`session.start_time`).
- **Auto-checkout.** `end_session()` checkar ut kvarvarande deltagare fore stangning.
- **Ljud + visuell feedback.** Kiosken anvander Web Audio API for checkin/checkout/fel-toner och CSS-animationer pa QR-ramen.

## Testmonster

- Tester i `tests/test_api_flows.py` — **mockar crud-funktioner**, ingen databas
- `@patch.object(crud, "get_open_session", return_value=...)` osv
- **Kor INTE** mot SQLite eller Postgres — rent unit-test-lager
- `pytest` — 31 tester, alla grona

## API-endpoints

| Metod | Path | Auth | Beskrivning |
|-------|------|------|-------------|
| GET | `/kiosk` | - | Checkin-vy (QR-skanning) |
| GET | `/admin` | PIN | Admin-dashboard |
| POST | `/api/checkin` | - | QR checkin `{qr_data}` |
| POST | `/api/link-and-checkin` | - | Koppla kort + checkin `{card_id, player_name}` |
| POST | `/api/sessions/start` | PIN | Starta session `{location, notes}` |
| POST | `/api/sessions/end` | PIN | Avsluta session |
| GET | `/api/sessions/open` | - | Oppna session |
| GET | `/api/sessions/attendance` | - | Narvarolista |
| POST | `/api/headcount` | PIN | Registrera headcount `{count}` |
| GET | `/api/headcount` | - | Hamta headcounts |
| POST | `/api/checkin/{id}/undo-checkout` | PIN | Angra utcheckning |
| DELETE | `/api/checkin/{id}` | PIN | Ta bort checkin |
| GET | `/admin/history` | PIN | Sessionshistorik |
| GET | `/admin/members` | PIN | Spelarlista |
| GET | `/admin/stats` | PIN | Statistik |
| GET | `/admin/export` | PIN | CSV-export |
| GET | `/admin/audit` | PIN | Audit-logg |

## Dokumentation

- `docs/ARCHITECTURE.md` — Systemarkitektur, datafloden, deploy
- `docs/API-REFERENCE.md` — Komplett API-referens med request/response-exempel
- `docs/DATA-MODEL.md` — Databasschema, relationer, affarsregler, CRUD-funktioner

## Vad som ATERSTAR (se ROADMAP.md for detaljer)

1. Samla mer live-feedback (sondagstraffen 2026-03-29)
2. Insights/analytics fran meetup-data
3. Insights-integration med turneringssystemet
4. Spelarstatistik pa medlemskortet

## Viktiga regler

- **Skriv inte SQLAlchemy-kod.** Systemet anvander psycopg3 raw SQL.
- **Skapa inte tabeller.** Tabellerna ags av `fgt-checkin-system/init.sql`.
- **Mocka crud i tester.** Anvand `@patch.object(crud, ...)`, inte SQLite.
- **`players` ar read-only** fran detta system. Skapa/uppdatera spelare gors i turneringssystemet.
- **Personnummer lagras aldrig.** GDPR — anvands bara for realtidsverifiering mot eBas.

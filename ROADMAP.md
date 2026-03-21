# FGC THN — Unified System Roadmap

Senast uppdaterad: 2026-03-21

## Vision
Tre system, en Postgres, en spelaridentitet. Checka in en gång → syns överallt.

---

## Status per system

| System | Repo | Status |
|--------|------|--------|
| Turneringar | `fgt-checkin-system` | Produktion |
| Medlemskort | `fgt-member-card` | DEV kör, behöver polish |
| Meetups | `fgc-thn-meetups` | Arbetsorder klar, migrering ej påbörjad |

---

## TODO

### Medlemskort (fgt-member-card)

- [x] Arkitektur och design bestämd
- [x] Frontend: kort med QR, sociala länkar, FGC THN-branding
- [x] Backend: FastAPI + psycopg3, läser players + card_ids
- [x] Personnummer + tag verifiering mot eBas via n8n
- [x] Cookie-baserad session (behöver inte logga in igen)
- [x] GDPR-text på landing page
- [x] Docker-setup (dev), ansluter till turneringssystemets nätverk
- [ ] Byt logotyp till transparent bakgrund (väntar på fil från Viktor)
- [ ] Visa spelarstatistik på kortet (antal events, favorite game, streak)
- [ ] DNS: sätt upp `medlemskort.fgctrollhattan.se` A-record på One.com
- [ ] SSL: certbot för medlemskort-domänen
- [ ] Prod-deploy på Raspberry Pi
- [ ] Testa med riktiga medlemmar

### Meetup-migrering (fgc-thn-meetups)

- [x] Arkitekturbeslut: raw SQL + psycopg3 (samma som turneringssystemet)
- [x] Meetup-tabeller skapade i Postgres (meetup_sessions, meetup_checkins, meetup_headcounts)
- [x] card_ids-tabell skapad
- [x] Schema verifierat (kolumnnamn matchar arbetsorder)
- [x] Arbetsorder skriven (ARBETSORDER-MIGRERING.md)
- [ ] **Kör migreringen** (Codex eller manuellt via arbetsorder)
  - [ ] db.py — byt till psycopg3 connection pool
  - [ ] crud.py — skriv om alla funktioner till raw SQL
  - [ ] deps.py — ta bort SQLAlchemy-beroende, uppdatera extract_token för card_ids
  - [ ] config.py — Postgres URL som default
  - [ ] main.py — ta bort create_all
  - [ ] routers — uppdatera alla tre (kiosk, admin, reports)
  - [ ] templates — Member → Player namnbyte
  - [ ] Ta bort models.py och SQLite-filer
- [ ] Docker-setup för meetup-systemet
- [ ] Testa hela flödet: session → QR-checkin → gäst-checkin → headcount → statistik
- [ ] Registreringsformulär för gäst → medlem (återanvänd från turneringssystemet)

### Turneringssystemet (fgt-checkin-system)

- [x] Meetup-tabeller tillagda i init.sql + _run_migrations()
- [x] card_ids-tabell tillagd
- [x] Schema fixat (checkin_time/checkout_time/created_by)
- [x] eBas webhook (ebas/check) verifierad — fungerar för medlemskort
- [x] Kontext delad med andra agenter (project_unified_ecosystem.md)
- [ ] Framtid: Insights "Meetups"-flik (läser meetup_checkins)
- [ ] Framtid: Insights "Overview" med kombinerad historik

### Infrastruktur

- [ ] DNS: `medlemskort.fgctrollhattan.se` → Pi:ns IP (One.com)
- [ ] Docker-prefix bestämda: `fgt-card-dev/prod`, `fgt-meetup-dev/prod`
- [ ] SSL-cert för nya domäner
- [ ] Testa att alla tre system kör samtidigt på Pi:n

---

## Ordning att jobba i

1. **Nästa:** Kör meetup-migreringen (arbetsorder finns)
2. **Sen:** Testa hela kedjan end-to-end (turnering → kort → meetup)
3. **Sen:** DNS + SSL + prod-deploy av medlemskort
4. **Sen:** Registreringsformulär för nya medlemmar på meetups
5. **Framtid:** Insights-integration, statistik över alla system

---

## Sociala länkar (referens)

- Discord: https://discord.gg/tPDaSTgPm6
- YouTube: https://www.youtube.com/@smashtrolls6538
- Twitch: https://www.twitch.tv/fgctrollhattan
- Twitch 2: https://www.twitch.tv/fgctrollhattan2

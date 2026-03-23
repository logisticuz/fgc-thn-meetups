# FGC THN — Unified System Roadmap

Senast uppdaterad: 2026-03-23

## Vision
Tre system, en Postgres, en spelaridentitet. Checka in en gang → syns overallt.

---

## Status per system

| System | Repo | Status |
|--------|------|--------|
| Turneringar | `fgt-checkin-system` | Produktion |
| Medlemskort | `fgt-member-card` | DEV kor, behover polish |
| Meetups | `fgc-thn-meetups` | Feature-complete, behover E2E-test + prod-deploy |

---

## TODO

### Meetup-system (fgc-thn-meetups)

- [x] Arkitekturbeslut: raw SQL + psycopg3 (samma som turneringssystemet)
- [x] Meetup-tabeller skapade i Postgres (meetup_sessions, meetup_checkins, meetup_headcounts)
- [x] card_ids-tabell skapad
- [x] Schema verifierat (kolumnnamn matchar arbetsorder)
- [x] Arbetsorder skriven och genomford
- [x] db.py — psycopg3 connection pool
- [x] crud.py — alla funktioner omskrivna till raw SQL
- [x] deps.py — ORM-beroende borttaget, extract_token for card_ids
- [x] config.py — Postgres URL som default
- [x] main.py — create_all borttagen
- [x] routers — alla tre uppdaterade (kiosk, admin, reports)
- [x] templates — Member → Player namnbyte
- [x] models.py borttagen
- [x] Testsvit omskriven (31 tester, mock-baserade)
- [x] Repo publikt pa GitHub
- [x] Dockerfile + docker-compose.dev.yml
- [x] Gast → medlem-registrering (kiosk + admin, Luhn-validering, n8n/eBas-integration)
- [ ] E2E-test mot riktig Postgres: session → QR-checkin → gast → bli medlem → headcount → statistik → export
- [ ] docker-compose.prod.yml + nginx.conf
- [ ] Prod-deploy pa Raspberry Pi

### Medlemskort (fgt-member-card)

- [x] Arkitektur och design bestamd
- [x] Frontend: kort med QR, sociala lankar, FGC THN-branding
- [x] Backend: FastAPI + psycopg3, laser players + card_ids
- [x] Personnummer + tag verifiering mot eBas via n8n
- [x] Cookie-baserad session (behover inte logga in igen)
- [x] GDPR-text pa landing page
- [x] Docker-setup (dev), ansluter till turneringssystemets natverk
- [ ] Byt logotyp till transparent bakgrund (vantar pa fil fran Viktor)
- [ ] Visa spelarstatistik pa kortet (antal events, favorite game, streak)
- [ ] DNS: satt upp `medlemskort.fgctrollhattan.se` A-record pa One.com
- [ ] SSL: certbot for medlemskort-domanen
- [ ] Prod-deploy pa Raspberry Pi
- [ ] Testa med riktiga medlemmar

### Turneringssystemet (fgt-checkin-system)

- [x] Meetup-tabeller tillagda i init.sql + _run_migrations()
- [x] card_ids-tabell tillagd
- [x] Schema fixat (checkin_time/checkout_time/created_by)
- [x] eBas webhook (ebas/check) verifierad — fungerar for medlemskort
- [x] Kontext delad med andra agenter (project_unified_ecosystem.md)
- [ ] Framtid: Insights "Meetups"-flik (laser meetup_checkins)
- [ ] Framtid: Insights "Overview" med kombinerad historik

### Infrastruktur

- [ ] DNS: `medlemskort.fgctrollhattan.se` → Pi:ns IP (One.com)
- [ ] Docker-prefix bestamda: `fgt-card-dev/prod`, `fgt-meetup-dev/prod`
- [ ] SSL-cert for nya domaner
- [ ] Testa att alla tre system kor samtidigt pa Pi:n

---

## Nasta steg (prioritetsordning)

1. **Nu:** E2E-test av meetup-systemet mot riktig Postgres + n8n
2. **Nasta:** Prod-config for meetup (docker-compose.prod.yml + nginx)
3. **Sen:** DNS + SSL + prod-deploy av medlemskort
4. **Sen:** Testa hela kedjan end-to-end (turnering → kort → meetup)
5. **Framtid:** Spelarstatistik pa medlemskortet
6. **Framtid:** Insights-integration, statistik over alla system

---

## Sociala lankar (referens)

- Discord: https://discord.gg/tPDaSTgPm6
- YouTube: https://www.youtube.com/@smashtrolls6538
- Twitch: https://www.twitch.tv/fgctrollhattan
- Twitch 2: https://www.twitch.tv/fgctrollhattan2

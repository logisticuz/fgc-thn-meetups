# FGC THN — Unified System Roadmap

Senast uppdaterad: 2026-03-29

## Vision
Tre system, en Postgres, en spelaridentitet. Checka in en gang → syns overallt.

---

## Status per system

| System | Repo | Status |
|--------|------|--------|
| Turneringar | `fgt-checkin-system` | Produktion |
| Medlemskort | `fgt-member-card` | Produktion (membercard.fgctrollhattan.se) |
| Meetups | `fgc-thn-meetups` | Produktion (meetup.fgctrollhattan.se) |

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
- [x] E2E-test mot riktig Postgres (dev + prod)
- [x] docker-compose.prod.yml
- [x] Prod-deploy pa Raspberry Pi (port 8004, 1 worker)
- [x] DNS: meetup.fgctrollhattan.se → 213.89.64.103 (One.com)
- [x] SSL: Let's Encrypt via certbot (giltigt till 2026-06-22)
- [x] Nginx reverse proxy (dockeriserad, delar config med checkin-system)
- [x] Sakerhets-hardening: auth gate (login-sida), PIN-lockout (5 forsok, 15 min)
- [x] Forsta live-test genomfort (2026-03-25, 7 incheckade)
- [x] Auto-checkout vid session-avslut
- [x] Admin angra checkout (aterställ utcheckning utan att radera)
- [x] Checkin/checkout-ljud (Web Audio API, olika toner for in/ut/fel)
- [x] QR visuell feedback (kameraramen flashar gront/cyan/rott)
- [x] Kalender multi-session (tabs vid flera sessioner per dag)
- [x] Timezone-fix (Europe/Stockholm pa connection-niva)
- [x] "Kiosk" → "Checkin" namnbyte i nav
- [x] Bugfix: kalender dag-detalj krasch (dubbel isoformat)
- [x] Refaktor: crud returnerar ra datetime istallet for strangar
- [ ] Sakerhets-hardening: security headers, CSRF, session timeout (laag prio)

### Medlemskort (fgt-member-card)

- [x] Arkitektur och design bestamd
- [x] Frontend: kort med QR, sociala lankar, FGC THN-branding
- [x] Backend: FastAPI + psycopg3, laser players + card_ids
- [x] Personnummer + tag verifiering mot eBas via n8n
- [x] Cookie-baserad session (behover inte logga in igen)
- [x] GDPR-text pa landing page
- [x] Docker-setup (dev), ansluter till turneringssystemets natverk
- [x] DNS: `membercard.fgctrollhattan.se` A-record pa One.com
- [x] SSL: Let's Encrypt via certbot
- [x] Prod-deploy pa Raspberry Pi (port 8003, deploy 2026-03-24)
- [x] Nginx reverse proxy + HTTPS redirect
- [ ] Byt logotyp till transparent bakgrund (vantar pa fil fran Viktor)
- [ ] Visa spelarstatistik pa kortet (antal events, favorite game, streak)
- [x] Testa med riktiga medlemmar (live-test 2026-03-25, QR + checkin fungerade)

### Turneringssystemet (fgt-checkin-system)

- [x] Meetup-tabeller tillagda i init.sql + _run_migrations()
- [x] card_ids-tabell tillagd
- [x] Schema fixat (checkin_time/checkout_time/created_by)
- [x] eBas webhook (ebas/check) verifierad — fungerar for medlemskort
- [x] Kontext delad med andra agenter (project_unified_ecosystem.md)
- [ ] Framtid: Insights "Meetups"-flik (laser meetup_checkins)
- [ ] Framtid: Insights "Overview" med kombinerad historik

### Infrastruktur

- [x] DNS: `meetup.fgctrollhattan.se` → Pi:ns IP (One.com)
- [x] Meetup + Checkin kor sida vid sida pa Pi 4 (~1.5 GiB ledigt RAM)
- [x] DNS: `membercard.fgctrollhattan.se` → Pi:ns IP (One.com)
- [x] SSL-cert for medlemskort (Let's Encrypt)
- [ ] Docker-prefix bestamda: `fgt-card-dev/prod`, `fgt-meetup-dev/prod`
- [ ] Sakerhets-hardening for alla system (gemensam insats, laag prio)

---

## Nasta steg (prioritetsordning)

1. **Nu:** Samla mer live-feedback (sondagstraffen 2026-03-29)
2. **Nasta:** Spelarstatistik pa medlemskortet (events, favorit-spel, streak)
3. **Sen:** Insights/analytics fran meetup-data (peak fran checkin-tider, trender, retention)
4. **Sen:** Testa hela kedjan end-to-end (turnering → kort → meetup)
5. **Laag prio:** Security headers, CSRF, session timeout

---

## Sociala lankar (referens)

- Discord: https://discord.gg/tPDaSTgPm6
- YouTube: https://www.youtube.com/@smashtrolls6538
- Twitch: https://www.twitch.tv/fgctrollhattan
- Twitch 2: https://www.twitch.tv/fgctrollhattan2

# Arbetsorder: Uppdatera meetup-systemet pa prod (Pi 4)

## Mal

Pulla senaste koden och bygga om containern. Nya features sedan forsta deploy:

### Batch 1 (redan deployat)
- **Auth gate** — login-sida kraver PIN for att komma in (alla sidor)
- **PIN-lockout** — 5 forsok, 15 min lockout
- **Admin-tabs** — "Traff" + "Oversikt" istallet for allt pa en sida
- **Namnsok pa kiosken** — medlemmar utan kort kan checka in via namn
- **Forinst alld plats** — kiosken har Studiefr amjandet som default

### Batch 2 (denna deploy)
- **Kalender** — manadsvy i Oversikt-fliken, klickbara dagar med sessionsdetaljer
- **Kassa** — registrera kioskintakter per session (ny kolumn i databasen)
- **Dev tab** — dold flik for dev-PIN, session-radering med cascade-delete
- **Favicon** — `/static/assets/favicon.png`
- **Footer** — "Powered by IMLO" i botten, `background-attachment: fixed` for att inte bryta gradienten

## Steg

### 1. Ga till repot

```bash
cd /home/viktor/fgc-thn-meetups
```

### 2. Pulla senaste

```bash
git pull origin main
```

### 3. Databasmigering (VIKTIGT — gor FORE omstart)

Kassa-funktionen kraver en ny kolumn. Kor mot Postgres:

```bash
docker exec -it fgt-checkin-system-postgres-1 psql -U fgc -d fgc_checkin -c \
  "ALTER TABLE meetup_sessions ADD COLUMN IF NOT EXISTS kiosk_revenue NUMERIC(10,2) DEFAULT 0;"
```

Verifiera:

```bash
docker exec -it fgt-checkin-system-postgres-1 psql -U fgc -d fgc_checkin -c \
  "\d meetup_sessions"
```

`kiosk_revenue` ska synas i kolumnlistan.

### 4. Kontrollera .env

Filen maste ha foljande:

```
ADMIN_PIN=<admin-pin>
DEV_PIN=<dev-pin>
SECRET_KEY=<nagot-langtt-random>
DATABASE_URL=postgresql://fgc:<POSTGRES_PASSWORD>@postgres:5432/fgc_checkin
```

**Nytt:** `DEV_PIN` — separat PIN for dev-access. Utan den ar dev-tabben otillganglig (som det ska vara om man inte vill ha den).

Om `SECRET_KEY` saknas, generera en:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Bygg om och starta

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 6. Verifiera att containern kor

```bash
docker ps | grep meetup
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/login
# Forvantat: 200
```

### 7. Testa nya features

```bash
# Auth gate (borde redan funka fran forra deployen)
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/admin
# Forvantat: 302 (redirect till /login)

# Kalender-API
# (kraver inloggad session, testa via webblasaren)

# Favicon
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/static/assets/favicon.png
# Forvantat: 200
```

Manuell test i webblasaren:
- [ ] Logga in med admin-PIN → ser Traff + Oversikt (INTE Dev)
- [ ] Oversikt-fliken visar kalender med sessioner markerade
- [ ] Traff-fliken visar Kassa-kort
- [ ] Logga in med dev-PIN → ser Traff + Oversikt + Dev (rod flik)
- [ ] Dev-fliken listar sessioner med radera-knappar
- [ ] Favicon syns i webblasarfliken
- [ ] "Powered by IMLO" syns langst ner, bakgrund ar inte trasig

### 8. Testa via HTTPS

```bash
curl -s -o /dev/null -w '%{http_code}' https://meetup.fgctrollhattan.se/login
# Forvantat: 200
```

### 9. Nginx

Ingen andring kravs — samma port (8004), samma server block.

## Klart-kriterier

- [ ] `git pull` lyckades
- [ ] `ALTER TABLE` korde utan fel
- [ ] `kiosk_revenue`-kolumn finns i `meetup_sessions`
- [ ] `.env` har `DEV_PIN` satt
- [ ] Container kor (`docker ps`)
- [ ] `/login` svarar 200
- [ ] Kalender visas i Oversikt
- [ ] Kassa-kort visas i Traff
- [ ] Dev-tab syns BARA med dev-PIN
- [ ] Favicon laddas
- [ ] Footer bryter inte bakgrundsgradienten
- [ ] HTTPS fungerar

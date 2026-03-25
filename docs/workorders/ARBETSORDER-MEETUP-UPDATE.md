# Arbetsorder: Uppdatera meetup-systemet pa prod (Pi 4)

## Mal

Pulla senaste koden och bygga om containern. Nya features sedan deploy:

- **Auth gate** — login-sida kraver PIN for att komma in (alla sidor)
- **PIN-lockout** — 5 forsok, 15 min lockout
- **Admin-tabs** — "Traff" + "Oversikt" istallet for allt pa en sida
- **Namnsok pa kiosken** — medlemmar utan kort kan checka in via namn
- **Forinst alld plats** — kiosken har Studiefr amjandet som default
- **Forenklad session-start** — en knapp, ingen formularprompt

## Steg

### 1. Ga till repot

```bash
cd /home/viktor/fgc-thn-meetups
```

### 2. Pulla senaste

```bash
git pull origin main
```

### 3. Kontrollera .env

Filen maste ha foljande:

```
ADMIN_PIN=fgcthn2016!
SECRET_KEY=<nagot-langtt-random>
DATABASE_URL=postgresql://fgc:<POSTGRES_PASSWORD>@postgres:5432/fgc_checkin
```

`SECRET_KEY` anvands av SessionMiddleware for cookie-signering.
Om den inte finns, generera en:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Lagg till raden `SECRET_KEY=<output>` i `.env`.

### 4. Bygg om och starta

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 5. Verifiera att containern kor

```bash
docker ps | grep meetup
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/login
# Forvantat: 200
```

### 6. Testa auth gate

```bash
# Utan session → redirect till /login
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/admin
# Forvantat: 302 (redirect till /login)

curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/kiosk
# Forvantat: 302 (redirect till /login)

# Login-sidan sjalv ska vara tillganglig
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/login
# Forvantat: 200

# Static assets ska vara tillgangliga
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8004/static/styles.css
# Forvantat: 200
```

### 7. Testa via HTTPS

```bash
curl -s -o /dev/null -w '%{http_code}' https://meetup.fgctrollhattan.se/login
# Forvantat: 200

curl -s -o /dev/null -w '%{http_code}' https://meetup.fgctrollhattan.se/admin
# Forvantat: 302 → /login
```

### 8. Nginx

Ingen andring kravs i nginx — samma port (8004), samma server block.

## Viktigt: SessionMiddleware

Auth gate anvander cookies via Starlettes SessionMiddleware. Den kraver
`SECRET_KEY` i `.env`. Utan den startar inte appen.

Om appen inte startar, kolla loggar:

```bash
docker compose -f docker-compose.prod.yml logs --tail 50 backend
```

## Klart-kriterier

- [ ] `git pull` lyckades
- [ ] Container kor (`docker ps`)
- [ ] `/login` svarar 200
- [ ] `/admin` redirectar till `/login` (302)
- [ ] `/kiosk` redirectar till `/login` (302)
- [ ] Inloggning med PIN fungerar
- [ ] Admin visar tabs (Traff + Oversikt)
- [ ] HTTPS fungerar

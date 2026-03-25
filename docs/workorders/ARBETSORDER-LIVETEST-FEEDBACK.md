# Arbetsorder: Deploy live-test feedback (Pi 4)

## Mal

Pulla senaste koden och bygga om containern. Andringar baserade pa feedback fran forsta riktiga traffen (2026-03-25).

### Nya features och fixar

- **Auto-checkout** — nar admin avslutar sessionen checkas alla kvarvarande deltagare ut automatiskt
- **Angra checkout** — admin kan angra en utcheckning (ny knapp i narvarolistan) istallet for att behova radera och checka in pa nytt
- **Checkin/checkout-ljud** — olika toner for incheckning (stigande), utcheckning (fallande) och fel (buzz)
- **QR visuell feedback** — kameraramen flashar gront (checkin), cyan (checkout) eller rott (fel) vid skanning
- **Kalender multi-session** — om det finns flera sessioner pa en dag visas tabs for att valja mellan dem
- **Timezone-fix** — alla tider visas nu i svensk tid (Europe/Stockholm), fixar att session-starttid visades en timme fel
- **"Kiosk" → "Checkin"** — navlanken heter nu "Checkin" istallet for "Kiosk" for att undvika forvirring med snack-kiosken
- **Bugfix: kalender dag-detalj** — fixat krasch vid klick pa dagar med headcount-data (dubbel isoformat)
- **Refaktor: crud datetime** — crud returnerar nu ratt datetime-objekt istallet for strangar, forenklad for framtida insights/analytics

## Steg

### 1. Ga till repot

```bash
cd /home/viktor/fgc-thn-meetups
```

### 2. Pulla senaste

```bash
git pull origin main
```

### 3. Databasmigering

Ingen databasmigering kravs denna gang. Alla andringar ar i applikationskod, JavaScript och CSS.

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

### 6. Testa nya features

Manuell test i webblasaren:

**Checkin-sidan (fd. Kiosk):**
- [ ] Navlanken visar "Checkin" (inte "Kiosk")
- [ ] Starta session → notera att starttiden stammer med svensk tid
- [ ] Skanna QR-kod → hors ett stigande pip-ljud, kameraramen flashar gront
- [ ] Skanna samma QR igen → hors ett fallande pip-ljud (checkout), ramen flashar cyan, meddelande "Hej da [namn]!"
- [ ] Skanna en okand QR → hors buzz-ljud, ramen flashar rott

**Admin-sidan:**
- [ ] Narvarolistan visar en angra-knapp (↩) bredvid utcheckade deltagare
- [ ] Klicka angra → personen blir "har" igen
- [ ] Avsluta session → alla kvarvarande auto-checkas ut
- [ ] Kontrollera att logg-raden visar "X auto-checked out"

**Kalender (Oversikt-fliken):**
- [ ] Om en dag har flera sessioner visas tabs med sessionstider
- [ ] Klicka mellan tabs → visar ratt statistik for varje session
- [ ] Enstaka sessioner fungerar som vanligt (inga tabs)

### 7. Testa via HTTPS

```bash
curl -s -o /dev/null -w '%{http_code}' https://meetup.fgctrollhattan.se/login
# Forvantat: 200
```

### 8. Nginx

Ingen andring kravs — samma port (8004), samma server block.

## Klart-kriterier

- [ ] `git pull` lyckades
- [ ] Container kor (`docker ps`)
- [ ] `/login` svarar 200
- [ ] Navlank visar "Checkin"
- [ ] Session-starttid stammer med svensk tid
- [ ] Ljud hors vid checkin/checkout/fel
- [ ] QR-ramen flashar ratt farg
- [ ] Angra-checkout funkar i narvarolistan
- [ ] Auto-checkout vid session-avslut fungerar
- [ ] Kalender hanterar flera sessioner per dag
- [ ] HTTPS fungerar

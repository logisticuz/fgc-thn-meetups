# Designförslag: Gäst → Medlem-registrering i meetup-systemet

## Bakgrund

Meetup-systemet behöver ett flöde där gäster som checkat in på träffar kan bli
Sverok-medlemmar direkt från meetup-kiosken. Idag finns inget sådant flöde —
gäster förblir gäster tills de registrerar sig via turneringssystemet.

## Krav

- **Samma data som turneringsregistreringen** — det får inte diffa.
- Minimalt: personnummer (eBas-krav) + tag (players-krav). Namn har vi redan från guest_name.
- Valfritt: telefon, email.

## Exempelflöde: Joel → joelboy

1. Joel checkar in som gäst → `guest_name: "Joel"` sparas i checkin.
2. Joel klickar **"Bli medlem"** i kiosk-vyn.
3. Formulär visas med:
   - **Tag** (obligatoriskt) → `"joelboy"`
   - **Personnummer** (obligatoriskt) → `200XXXXXXXXX`
   - Telefon (valfritt)
   - Email (valfritt)
4. Meetup-systemet:
   - Skapar en `player` i `players`-tabellen: `name="Joel"`, `tag="joelboy"`, telefon, email
   - Skickar personnummer + valfria fält till n8n för eBas-registrering
   - Uppdaterar checkin: kopplar `player_uuid`, tar bort `guest_name`
5. Joel syns nu som spelare "joelboy", inte gäst "Joel".

## Arkitektur: Meetup → n8n direkt

```
┌──────────────┐         ┌──────────────┐         ┌──────────┐
│  meetup-app  │  POST   │     n8n      │  POST   │  Sverok  │
│  (port 8004) │ ──────→ │ (port 5678)  │ ──────→ │  eBas    │
│              │         │              │         │  API     │
└──────────────┘         └──────────────┘         └──────────┘
       │                        │
       │  Docker: fgt-dev_fgt-net (alla på samma nätverk)
       │
       ▼
┌──────────────┐
│   Postgres   │
│  fgc_checkin │
│  (players,   │
│   checkins)  │
└──────────────┘
```

### Varför n8n direkt och inte via turneringssystemet?

1. **n8n är den gemensamma integrationspunkten** — den äger eBas-logiken, inte turneringssystemet.
2. **Inget beroende på turneringssystemets backend** — meetup ska kunna köra standalone.
3. **Samma webhook**: `http://n8n:5678/webhook/ebas/register-v2` — beprövat, redan i drift.
4. **Turneringssystemet gör bara validering + forward** — vi lägger samma validering i meetup.

### Vad n8n-webhooket förväntar sig

```json
{
  "personnummer": "200XXXXXXXXX",
  "email": "",
  "telephone": "",
  "tag": "joelboy",
  "slug": "meetup",
  "checkin_id": ""
}
```

n8n normaliserar personnummer till 12 siffror, sätter `renewed` till dagens datum,
och anropar `https://ebas.sverok.se/apis/submit_member_with_lookup.json`.

eBas/SPAR slår upp förnamn + efternamn automatiskt via personnummer —
vi behöver INTE samla in dessa.

### Validering vi behöver implementera

Kopieras från turneringssystemets `validation.py`:

- **Personnummer**: 10-12 siffror, Luhn-checksumma, månad 01-12, dag 01-31
- **Telefon**: minst 7 siffror (om angiven), sanitera till bara siffror
- **Email**: max 254 tecken (om angiven)
- **Tag**: max 30 tecken

## Nya endpoints i meetup-systemet

### `POST /api/guest/register`

Request:
```json
{
  "checkin_id": "uuid-of-guest-checkin",
  "tag": "joelboy",
  "personnummer": "200XXXXXXXXX",
  "telephone": "",
  "email": ""
}
```

Backend-logik:
1. Hämta checkin → verifiera att det är en gäst (har `guest_name`, saknar `player_uuid`)
2. Validera personnummer (Luhn), tag (max 30), telefon/email om angivna
3. Skapa player i `players`-tabellen: `name=checkin.guest_name`, `tag`, `telephone`, `email`
4. Uppdatera checkin: sätt `player_uuid`, nollställ `guest_name`
5. POST till `http://n8n:5678/webhook/ebas/register-v2` med personnummer + fält
6. Returnera `{ "success": true, "player_uuid": "...", "ebas_status": "sent" }`

### Kiosk-UI

Knappen "Bli medlem" visas bredvid gästens namn i incheckningslistan.
Klick öppnar en modal/formulär med tag + personnummer + valfria fält.

## Beslut (feedback från fgt-checkin-system-agenten)

### 1. Callback-hantering → Fire-and-forget

Skicka `checkin_id: ""`. Svaret kommer **synkront** — n8n-workflowen har
`responseMode: "lastNode"` så eBas-resultatet returneras direkt i HTTP-responsen.

Callbacken till `POST /api/checkin/{checkin_id}/member-status` görs parallellt
men med `neverError: true` + `onError: continueRegularOutput` — den failar tyst
om endpointen inte finns. Inget problem för meetup.

```python
resp = await client.post(f"{N8N_URL}/webhook/ebas/register-v2", json=payload)
result = resp.json()  # {"success": true, "registered": true, "message": "..."}
```

### 2. Validering → Kopiera, inte delat bibliotek

Kopiera `validation.py` från turneringssystemet. Tre separata repos med egna
Docker-images — ett delat paket innebär ytterligare ett beroende att versionera.
Personnummer-Luhn ändras inte. Samma beslut gjordes för member-card-systemet.

### 3. Slug → "meetup" fungerar

`slug` passas bara igenom i n8n — den skickas aldrig till eBas API:t.
Används bara i callbacken till turneringsbackenden (som vi inte behöver).

### 4. Edge cases att hantera

**Viktigt: kolla om tag redan finns i players innan CREATE.**
Om personen redan registrerats via turnering finns de i `players`.
Gör lookup först (`SELECT * FROM players WHERE LOWER(tag) = LOWER($1)`)
och koppla till befintlig player istället för att skapa dubblett.

Redan Sverok-medlem via annan förening? Inget problem — `submit_member_with_lookup`
registrerar eller förnyar oavsett.

### 5. "Redan medlem" → Inget specialfall

eBas `submit_member_with_lookup` gör **register-or-renew** — inte bara register.
Om personen redan är medlem förnyas medlemskapet och `stored_member: true`
returneras. Ingen felhantering behövs.

Enda felfallet: ogiltigt personnummer (SPAR-lookup misslyckas) → `member_errors`
i svaret, som vi visar som felmeddelande i UI.

## Uppdaterad backend-logik

`POST /api/guest/register`:

1. Hämta checkin → verifiera att det är en gäst (har `guest_name`, saknar `player_uuid`)
2. Validera personnummer (Luhn), tag (max 30), telefon/email om angivna
3. **Kolla om tag redan finns i players** → om ja, koppla befintlig player
4. Om ny: skapa player i `players`: `name=checkin.guest_name`, `tag`, `telephone`, `email`
5. Uppdatera checkin: sätt `player_uuid`, nollställ `guest_name`
6. POST till `http://n8n:5678/webhook/ebas/register-v2` (synkront svar)
7. Returnera `{ "success": true, "player_uuid": "...", "ebas_result": {...} }`

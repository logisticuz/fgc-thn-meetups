# Arbetsorder: Gäst → Medlem — Backend (Codex)

## Mål

Bygg backend-stödet för att konvertera en gäst-incheckning till en registrerad spelare.
Claude hanterar frontend, validering, n8n-integration och tester separat.

## Designdokument

Se `docs/design/GUEST-TO-MEMBER-REGISTRATION.md` för full kontext och beslut.

## Uppgifter

### 1. Nya CRUD-funktioner i `src/crud.py`

**`get_player_by_tag(tag: str) -> dict | None`**
```sql
SELECT uuid, name, tag, email, telephone
FROM players
WHERE LOWER(tag) = LOWER(%s)
```
Returnera dict via `_row_dict()` eller `None`.

**`create_player(name: str, tag: str, telephone: str = "", email: str = "") -> dict`**
```sql
INSERT INTO players (uuid, name, tag, telephone, email)
VALUES (gen_random_uuid(), %s, %s, %s, %s)
RETURNING uuid, name, tag, email, telephone
```
Returnera dict via `_row_dict()`.

**`convert_guest_to_player(checkin_id: str, player_uuid: str) -> dict | None`**
```sql
UPDATE checkins
SET player_uuid = %s, guest_name = NULL
WHERE id = %s
RETURNING *
```
Returnera uppdaterad checkin som dict, eller `None` om checkin inte finns.

### 2. Ny endpoint i `src/routers/kiosk.py`

**`POST /api/guest/register`**

Pydantic-modell:
```python
class GuestRegisterRequest(BaseModel):
    checkin_id: str
    tag: str
    personnummer: str
    telephone: str = ""
    email: str = ""
```

Logik:
1. Hämta checkin via `crud.get_checkin_by_id(checkin_id)` — ny CRUD-funktion om den inte finns
2. Verifiera att checkin har `guest_name` och saknar `player_uuid` (annars 400)
3. Anropa `validation.validate_personnummer(personnummer)` — importera från `src/validation.py` (Claude skapar denna fil)
4. Kolla `crud.get_player_by_tag(tag)`:
   - Om spelaren redan finns → använd befintlig `player_uuid`
   - Om ny → `crud.create_player(name=checkin["guest_name"], tag=tag, telephone=telephone, email=email)`
5. `crud.convert_guest_to_player(checkin_id, player_uuid)`
6. Anropa `ebas.register_member(personnummer, tag, email, telephone)` — importera från `src/ebas.py` (Claude skapar denna fil)
7. `crud.log_action("guest_registered", f"{tag} registered as member", "system")`
8. Returnera `{"success": True, "player_uuid": player_uuid, "ebas_result": result}`

### 3. Ny CRUD-funktion: `get_checkin_by_id`

Om den inte redan finns:
```sql
SELECT * FROM checkins WHERE id = %s
```

### 4. Lägg till httpx i `requirements.txt`

```
httpx==0.28.1
```

## Filer att ändra

| Fil | Ändring |
|-----|---------|
| `src/crud.py` | Lägg till `get_player_by_tag()`, `create_player()`, `convert_guest_to_player()`, `get_checkin_by_id()` |
| `src/routers/kiosk.py` | Lägg till `GuestRegisterRequest`-modell + `POST /api/guest/register` endpoint |
| `requirements.txt` | Lägg till `httpx==0.28.1` |

## Beroenden

- `src/validation.py` — Claude skapar denna (personnummer Luhn-validering)
- `src/ebas.py` — Claude skapar denna (n8n-integration)

Dessa filer kommer finnas innan Codex behöver dem. Om de inte finns ännu,
skriv endpointen med `# TODO: import validation` / `# TODO: import ebas`
som placeholder och gå vidare.

## Regler

- Använd `psycopg3` raw SQL, inte ORM
- Alla funktioner returnerar dict via `_row_dict(cursor, row)`
- Inga nya tabeller — `players` och `checkins` ägs av fgt-checkin-system
- Kör inte `CREATE TABLE` eller migrationer
- Skriv INTE tester — Claude hanterar det

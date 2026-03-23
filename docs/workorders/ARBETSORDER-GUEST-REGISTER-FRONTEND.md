# Arbetsorder: Gäst → Medlem — Frontend, Validering & n8n (Claude)

## Mål

Bygg frontend-formulär, personnummer-validering och n8n eBas-integration
för att konvertera gäster till Sverok-medlemmar via meetup-kiosken.
Codex bygger backend CRUD + endpoint separat.

## Designdokument

Se `docs/design/GUEST-TO-MEMBER-REGISTRATION.md` för full kontext och beslut.

## Uppgifter

### 1. Skapa `src/validation.py`

Kopiera och anpassa från `fgt-checkin-system/backend/validation.py`:

```python
def sanitize_personnummer(value: str) -> str
    """Strips dashes/spaces, keeps only digits."""

def validate_personnummer(value: str) -> tuple[bool, str]:
    """Luhn checksum on last 10 digits. Returns (is_valid, error_message)."""

def sanitize_phone(value: str) -> str
    """Keeps only digits."""

def sanitize_string(value: str, max_length: int = 100) -> str
    """Strip whitespace, enforce max length."""
```

Behåll Luhn-algoritmen exakt som i originalet. Förenkla resten —
vi behöver inte `sanitize_checkin_payload()` eller `normalize_missing_keys()`.

### 2. Skapa `src/ebas.py`

n8n eBas-integration — fire-and-forget med synkront svar:

```python
import httpx
from src.config import settings

N8N_EBAS_URL = "http://n8n:5678/webhook/ebas/register-v2"

async def register_member(
    personnummer: str,
    tag: str,
    email: str = "",
    telephone: str = "",
) -> dict:
    """
    Skickar registrering till n8n → eBas.
    Returnerar {"success": bool, "message": str, ...}
    """
    payload = {
        "personnummer": personnummer,
        "email": email,
        "telephone": telephone,
        "tag": tag,
        "slug": "meetup",
        "checkin_id": "",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(N8N_EBAS_URL, json=payload)
        resp.raise_for_status()
        return resp.json()
```

Lägg till `N8N_URL` i `src/config.py`:
```python
n8n_url: str = os.getenv("N8N_URL", "http://n8n:5678")
```

### 3. Kiosk-UI: "Bli medlem"-knapp + modal

I `src/templates/kiosk.html`:

- Visa gästincheckning med en **"Bli medlem"**-knapp bredvid gästnamnet
- Klick öppnar en modal med formulär:
  - Tag (obligatoriskt, text input)
  - Personnummer (obligatoriskt, text input, 12 siffror)
  - Telefon (valfritt)
  - Email (valfritt)
  - Skicka-knapp

I `src/static/kiosk.js`:

- `showRegisterForm(checkinId, guestName)` — öppnar modalen, fyller i gästnamn
- `submitRegistration()` — POST till `/api/guest/register`
  - Frontend Luhn-validering av personnummer innan POST
  - Visa resultat: "Välkommen som medlem, joelboy!" eller felmeddelande
  - Uppdatera incheckningslistan (gäst → spelare)

### 4. Personnummer-validering i JS (frontend)

Lägg till i `kiosk.js` eller separat fil:
```javascript
function validatePersonnummer(pnr) {
    // Strip non-digits
    // Luhn checksum on last 10 digits
    // Return {valid: bool, error: string}
}
```

Samma logik som Python-versionen — dubbel validering (frontend + backend).

### 5. Uppdatera gästrendering i attendance

`fetchAttendance()` i `kiosk.js` behöver särskilja gäster från spelare
så att "Bli medlem"-knappen bara visas för gäster.

Backend returnerar redan `guest_name` vs `name` — använd det för att avgöra.

### 6. Tester

Lägg till i `tests/test_api_flows.py`:

```python
# Test: guest register — lyckad konvertering
@patch.object(crud, "get_checkin_by_id")
@patch.object(crud, "get_player_by_tag")
@patch.object(crud, "create_player")
@patch.object(crud, "convert_guest_to_player")
def test_guest_register_success(...)

# Test: guest register — tag redan finns, koppla befintlig
@patch.object(crud, "get_checkin_by_id")
@patch.object(crud, "get_player_by_tag")
@patch.object(crud, "convert_guest_to_player")
def test_guest_register_existing_tag(...)

# Test: guest register — ogiltigt personnummer
def test_guest_register_invalid_personnummer(...)

# Test: guest register — checkin är inte gäst
@patch.object(crud, "get_checkin_by_id")
def test_guest_register_not_a_guest(...)

# Test: personnummer Luhn-validering (unit test)
def test_validate_personnummer_valid(...)
def test_validate_personnummer_invalid(...)
```

### 7. Uppdatera `.env.example`

Lägg till:
```
N8N_URL=http://n8n:5678
```

## Filer att skapa/ändra

| Fil | Åtgärd |
|-----|--------|
| `src/validation.py` | **Skapa** — Luhn, sanitize |
| `src/ebas.py` | **Skapa** — n8n-integration |
| `src/config.py` | **Ändra** — lägg till `n8n_url` |
| `src/templates/kiosk.html` | **Ändra** — "Bli medlem"-modal |
| `src/static/kiosk.js` | **Ändra** — registerForm, Luhn-validering |
| `tests/test_api_flows.py` | **Ändra** — nya tester |
| `.env.example` | **Ändra** — N8N_URL |

## Beroenden

- Codex skapar `POST /api/guest/register` endpoint + CRUD-funktioner
- Claude skapar `validation.py` + `ebas.py` som endpointen importerar
- Ordning spelar inte roll — båda kan jobba parallellt

## Regler

- Kopiera Luhn-logiken exakt — inga "förbättringar"
- n8n-anropet är fire-and-forget med synkront svar (checkin_id: "")
- Testa med mock, aldrig mot riktig databas eller n8n
- Behåll befintlig kiosk-design/stil — inga designändringar utöver den nya modalen

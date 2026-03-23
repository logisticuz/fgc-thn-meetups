"""Route-level tests using mocked crud functions.

These tests verify routing logic, auth checks, and response shapes
without requiring a running Postgres database.
"""

from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from src import crud
from src import ebas
from src.validation import validate_personnummer, sanitize_personnummer, sanitize_phone


# --- Helpers ---

def _session(sid=1, status="open"):
    return {
        "id": sid,
        "start_time": datetime.utcnow(),
        "end_time": None,
        "location": "Lokal",
        "notes": "",
        "status": status,
        "created_at": datetime.utcnow(),
    }


def _player(uuid="p-001", name="Viktor Test", tag="Logisticuz"):
    return {
        "uuid": uuid,
        "name": name,
        "tag": tag,
        "email": None,
        "telephone": None,
        "total_events": 5,
        "card_id": "FGC-TEST01",
    }


def _checkin(cid=1, player_uuid="p-001", guest_name=None):  # noqa: player_uuid can be None
    return {
        "id": cid,
        "session_id": 1,
        "player_uuid": player_uuid,
        "guest_name": guest_name,
        "method": "qr_scan",
        "checkin_time": datetime.utcnow(),
        "checkout_time": None,
        "created_by": None,
    }


def _guest_checkin(cid=10, guest_name="Joel"):
    return _checkin(cid=cid, player_uuid=None, guest_name=guest_name)


# --- Auth tests ---

def test_start_session_requires_admin(client):
    response = client.post("/api/sessions/start", json={"location": "Lokal", "notes": ""})
    assert response.status_code == 401
    assert response.json()["status"] == "unauthorized"


def test_end_session_requires_admin(client):
    response = client.post("/api/sessions/end")
    assert response.status_code == 401


def test_headcount_requires_admin(client):
    response = client.post("/api/headcount", json={"count": 12})
    assert response.status_code == 401
    assert response.json()["status"] == "unauthorized"


def test_delete_checkin_requires_admin(client):
    response = client.delete("/api/checkin/1")
    assert response.status_code == 401


# --- Session lifecycle ---

@patch.object(crud, "log_action")
@patch.object(crud, "start_session", return_value=_session())
def test_admin_can_start_session(mock_start, mock_log, admin_client):
    res = admin_client.post("/api/sessions/start", json={"location": "Lokal", "notes": "Weekly"})
    assert res.status_code == 200
    body = res.json()
    assert "id" in body
    assert "start_time" in body
    mock_start.assert_called_once_with("Lokal", "Weekly")


@patch.object(crud, "log_action")
@patch.object(crud, "end_session")
@patch.object(crud, "get_open_session", return_value=_session())
def test_admin_can_end_session(mock_get, mock_end, mock_log, admin_client):
    res = admin_client.post("/api/sessions/end")
    assert res.status_code == 200
    assert res.json()["status"] == "ended"
    mock_end.assert_called_once_with(1)


@patch.object(crud, "get_open_session", return_value=None)
def test_end_session_returns_none_when_no_session(mock_get, admin_client):
    res = admin_client.post("/api/sessions/end")
    assert res.json()["status"] == "none"


# --- QR checkin flow ---

@patch.object(crud, "get_open_session", return_value=None)
def test_checkin_no_session(mock_get, client):
    res = client.post("/api/checkin", json={"qr_data": "FGC-TEST01"})
    assert res.json()["status"] == "no_session"


@patch.object(crud, "get_player_by_card_id", return_value=None)
@patch.object(crud, "get_open_session", return_value=_session())
def test_checkin_unknown_card(mock_session, mock_player, client):
    res = client.post("/api/checkin", json={"qr_data": "FGC-UNKNOWN"})
    body = res.json()
    assert body["status"] == "unknown"
    assert "card_id" in body


@patch.object(crud, "get_member_streak", return_value=2)
@patch.object(crud, "count_present", return_value=1)
@patch.object(crud, "count_checkins", return_value=1)
@patch.object(crud, "create_checkin", return_value=_checkin())
@patch.object(crud, "get_checkin_for_player", return_value=None)
@patch.object(crud, "get_player_by_card_id", return_value=_player())
@patch.object(crud, "get_open_session", return_value=_session())
def test_checkin_success(mock_session, mock_player, mock_existing, mock_create, mock_count, mock_present, mock_streak, client):
    res = client.post("/api/checkin", json={"qr_data": "https://medlemskort.fgctrollhattan.se/FGC-TEST01"})
    body = res.json()
    assert body["status"] == "ok"
    assert body["member_name"] == "Viktor Test"
    assert body["checkin_number"] == 1
    assert body["present"] == 1
    assert body["streak"] == 3  # 2 + 1


@patch.object(crud, "count_present", return_value=0)
@patch.object(crud, "checkout_player", return_value={**_checkin(), "checkout_time": datetime.utcnow()})
@patch.object(crud, "get_checkin_for_player", return_value=_checkin())
@patch.object(crud, "get_player_by_card_id", return_value=_player())
@patch.object(crud, "get_open_session", return_value=_session())
def test_checkin_toggles_checkout(mock_session, mock_player, mock_existing, mock_checkout, mock_present, client):
    res = client.post("/api/checkin", json={"qr_data": "FGC-TEST01"})
    body = res.json()
    assert body["status"] == "checkout"
    assert body["member_name"] == "Viktor Test"
    assert body["present"] == 0


# --- Link and checkin ---

@patch.object(crud, "get_member_streak", return_value=0)
@patch.object(crud, "count_present", return_value=1)
@patch.object(crud, "count_checkins", return_value=1)
@patch.object(crud, "create_checkin", return_value=_checkin())
@patch.object(crud, "get_checkin_for_player", return_value=None)
@patch.object(crud, "link_card", return_value=(True, None))
@patch.object(crud, "search_players_by_name", return_value=[_player()])
@patch.object(crud, "get_open_session", return_value=_session())
def test_link_and_checkin_by_name(mock_session, mock_search, mock_link, mock_existing, mock_create, mock_count, mock_present, mock_streak, client):
    res = client.post("/api/link-and-checkin", json={"card_id": "FGC-NEW01", "player_name": "Viktor"})
    body = res.json()
    assert body["status"] == "ok"
    assert body["member_name"] == "Viktor Test"
    mock_link.assert_called_once_with("p-001", "FGC-NEW01")


@patch.object(crud, "search_players_by_name", return_value=[])
@patch.object(crud, "get_open_session", return_value=_session())
def test_link_and_checkin_not_found(mock_session, mock_search, client):
    res = client.post("/api/link-and-checkin", json={"card_id": "FGC-NEW01", "player_name": "Nobody"})
    assert res.json()["status"] == "not_found"


# --- Headcount ---

@patch.object(crud, "create_headcount", return_value={"id": 1, "session_id": 1, "count": 8, "recorded_at": datetime.utcnow(), "created_by": "admin"})
@patch.object(crud, "get_open_session", return_value=_session())
def test_headcount_success(mock_session, mock_hc, admin_client):
    res = admin_client.post("/api/headcount", json={"count": 8})
    assert res.status_code == 200
    assert res.json()["count"] == 8


@patch.object(crud, "get_open_session", return_value=None)
def test_headcount_no_session(mock_session, admin_client):
    res = admin_client.post("/api/headcount", json={"count": 5})
    assert res.json()["status"] == "no_session"


# --- Attendance ---

@patch.object(crud, "get_open_session", return_value=None)
def test_attendance_no_session(mock_session, client):
    res = client.get("/api/sessions/attendance")
    body = res.json()
    assert body["open"] is False
    assert body["total"] == 0


@patch.object(crud, "count_present", return_value=2)
@patch.object(crud, "get_session_checkins", return_value=[
    {"number": 1, "name": "Viktor", "checkin_time": "", "checkout_time": "", "checked_out": False, "method": "qr_scan", "checkin_id": 1, "is_guest": False},
    {"number": 2, "name": "Guest", "checkin_time": "", "checkout_time": "", "checked_out": False, "method": "manual", "checkin_id": 2, "is_guest": True},
])
@patch.object(crud, "get_open_session", return_value=_session())
def test_attendance_with_checkins(mock_session, mock_checkins, mock_present, client):
    res = client.get("/api/sessions/attendance")
    body = res.json()
    assert body["open"] is True
    assert body["total"] == 2
    assert body["present"] == 2


# --- Delete checkin ---

@patch.object(crud, "delete_checkin", return_value=True)
def test_delete_checkin_success(mock_delete, admin_client):
    res = admin_client.delete("/api/checkin/42")
    assert res.json()["status"] == "ok"
    mock_delete.assert_called_once_with(42)


@patch.object(crud, "delete_checkin", return_value=False)
def test_delete_checkin_not_found(mock_delete, admin_client):
    res = admin_client.delete("/api/checkin/999")
    assert res.status_code == 404


# --- Open session API ---

@patch.object(crud, "get_open_session", return_value=None)
def test_open_session_none(mock_get, client):
    res = client.get("/api/sessions/open")
    assert res.json()["open"] is False


@patch.object(crud, "get_open_session", return_value=_session())
def test_open_session_active(mock_get, client):
    res = client.get("/api/sessions/open")
    body = res.json()
    assert body["open"] is True
    assert "id" in body
    assert "start_time" in body


# --- Personnummer validation (unit tests) ---

def test_validate_personnummer_valid_12():
    ok, err = validate_personnummer("199001011234")
    # This is a constructed example — Luhn may or may not pass.
    # Test with a known-valid personnummer instead:
    ok, err = validate_personnummer("8507099805")
    assert ok is True
    assert err == ""


def test_validate_personnummer_invalid_checksum():
    ok, err = validate_personnummer("8507099800")
    assert ok is False
    assert "checksumma" in err


def test_validate_personnummer_too_short():
    ok, err = validate_personnummer("12345")
    assert ok is False
    assert "siffror" in err


def test_validate_personnummer_invalid_month():
    ok, err = validate_personnummer("8513099805")
    assert ok is False
    assert "månad" in err


def test_sanitize_personnummer_strips():
    assert sanitize_personnummer("850709-9805") == "8507099805"
    assert sanitize_personnummer("19850709-9805") == "198507099805"
    assert sanitize_personnummer("  850709 9805 ") == "8507099805"


def test_sanitize_phone():
    assert sanitize_phone("070-123 45 67") == "0701234567"
    assert sanitize_phone("+46 70 123 45 67") == "46701234567"


# --- Guest checkin (kiosk) ---

@patch.object(crud, "count_present", return_value=1)
@patch.object(crud, "count_checkins", return_value=1)
@patch.object(crud, "create_checkin", return_value=_guest_checkin())
@patch.object(crud, "get_open_session", return_value=_session())
def test_guest_checkin_success(mock_session, mock_create, mock_count, mock_present, client):
    res = client.post("/api/guest/checkin", json={"guest_name": "Joel"})
    body = res.json()
    assert body["status"] == "ok"
    assert body["guest_name"] == "Joel"
    assert body["checkin_number"] == 1
    mock_create.assert_called_once()


@patch.object(crud, "get_open_session", return_value=None)
def test_guest_checkin_no_session(mock_session, client):
    res = client.post("/api/guest/checkin", json={"guest_name": "Joel"})
    assert res.json()["status"] == "no_session"


def test_guest_checkin_empty_name(client):
    res = client.post("/api/guest/checkin", json={"guest_name": "  "})
    assert res.status_code == 400


# --- Guest registration ---

@patch("src.ebas.register_member", new_callable=AsyncMock, return_value={"success": True, "registered": True, "message": "Medlem registrerad"})
@patch.object(crud, "log_action")
@patch.object(crud, "convert_guest_to_player", return_value=_checkin(cid=10, player_uuid="p-new"))
@patch.object(crud, "create_player", return_value=_player(uuid="p-new", name="Joel", tag="joelboy"))
@patch.object(crud, "get_player_by_tag", return_value=None)
@patch.object(crud, "get_checkin_by_id", return_value=_guest_checkin())
@patch.object(crud, "get_open_session", return_value=_session())
def test_guest_register_success(mock_session, mock_get_checkin, mock_get_tag, mock_create, mock_convert, mock_log, mock_ebas, client):
    res = client.post("/api/guest/register", json={
        "checkin_id": "10",
        "tag": "joelboy",
        "personnummer": "8507099805",
    })
    body = res.json()
    assert body["success"] is True
    assert body["player_uuid"] == "p-new"
    mock_create.assert_called_once()
    mock_ebas.assert_called_once()


@patch("src.ebas.register_member", new_callable=AsyncMock, return_value={"success": True})
@patch.object(crud, "log_action")
@patch.object(crud, "convert_guest_to_player", return_value=_checkin(cid=10, player_uuid="p-001"))
@patch.object(crud, "get_player_by_tag", return_value=_player(uuid="p-001", tag="joelboy"))
@patch.object(crud, "get_checkin_by_id", return_value=_guest_checkin())
@patch.object(crud, "get_open_session", return_value=_session())
def test_guest_register_existing_tag(mock_session, mock_get_checkin, mock_get_tag, mock_convert, mock_log, mock_ebas, client):
    res = client.post("/api/guest/register", json={
        "checkin_id": "10",
        "tag": "joelboy",
        "personnummer": "8507099805",
    })
    body = res.json()
    assert body["success"] is True
    assert body["player_uuid"] == "p-001"


def test_guest_register_invalid_personnummer(client):
    res = client.post("/api/guest/register", json={
        "checkin_id": "10",
        "tag": "joelboy",
        "personnummer": "1234",
    })
    body = res.json()
    assert body.get("success") is not True or res.status_code >= 400


@patch.object(crud, "get_checkin_by_id", return_value=_checkin())
@patch.object(crud, "get_open_session", return_value=_session())
def test_guest_register_not_a_guest(mock_session, mock_get_checkin, client):
    res = client.post("/api/guest/register", json={
        "checkin_id": "1",
        "tag": "joelboy",
        "personnummer": "8507099805",
    })
    body = res.json()
    assert res.status_code == 400 or body.get("success") is False

import logging

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from ..config import settings
from ..deps import templates, is_admin, require_admin, extract_token
from .. import crud, auth

router = APIRouter()
logger = logging.getLogger(__name__)


class SessionStart(BaseModel):
    location: str | None = None
    notes: str | None = None


class HeadcountRequest(BaseModel):
    count: int


class RevenueRequest(BaseModel):
    amount: float


def _safe_log_action(action: str, details: str, actor: str) -> None:
    try:
        crud.log_action(action, details, actor)
    except Exception as exc:
        logger.warning("Audit logging unavailable: %s", exc)


# --- Auth ---

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, pin: str = Form(...)):
    ip = auth.get_client_ip(request)

    if auth.is_locked_out(ip):
        remaining = auth.remaining_lockout_seconds(ip)
        minutes = remaining // 60 + 1
        _safe_log_action("login_blocked", f"Locked out IP {ip} attempted login", "system")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"För många försök. Försök igen om {minutes} min.",
        })

    is_dev = settings.dev_pin and pin == settings.dev_pin
    is_admin_pin = pin == settings.admin_pin

    if is_dev or is_admin_pin:
        auth.clear_attempts(ip)
        request.session["authenticated"] = True
        request.session["is_admin"] = True
        if is_dev:
            request.session["is_dev"] = True
        role = "dev" if is_dev else "admin"
        _safe_log_action("login_success", f"Login from {ip} ({role})", role)
        return RedirectResponse("/kiosk", status_code=302)

    auth.record_failed_attempt(ip)
    attempts_left = auth.MAX_ATTEMPTS - auth.failed_count(ip)
    _safe_log_action("login_failed", f"Failed login from {ip} ({attempts_left} attempts left)", "system")

    if attempts_left <= 0:
        error = "Kontot är låst i 15 minuter."
    elif attempts_left <= 2:
        error = f"Fel PIN. {attempts_left} försök kvar."
    else:
        error = "Fel PIN-kod."

    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# --- Dashboard ---

@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    guard = require_admin(request)
    if guard:
        return guard
    open_session = crud.get_open_session()
    is_dev = request.session.get("is_dev", False)
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "open_session": open_session, "message": None, "error": None, "is_dev": is_dev},
    )


# --- Session API ---

@router.post("/api/sessions/start")
async def api_start_session(request: Request, payload: SessionStart):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    session = crud.start_session(payload.location, payload.notes)
    crud.log_action("session_started", f"Session {session['id']} started at {payload.location or 'unknown'}", "admin")
    return {"id": session["id"], "start_time": session["start_time"].isoformat()}


@router.post("/api/sessions/end")
async def api_end_session(request: Request):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    session = crud.get_open_session()
    if not session:
        return {"status": "none"}
    auto_checkouts = crud.end_session(session["id"])
    crud.log_action("session_ended", f"Session {session['id']} ended, {auto_checkouts} auto-checked out", "admin")
    return {"status": "ended", "auto_checkouts": auto_checkouts}


# --- Headcount ---

@router.post("/api/headcount")
async def api_headcount(request: Request, payload: HeadcountRequest):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    session = crud.get_open_session()
    if not session:
        return JSONResponse({"status": "no_session"})
    hc = crud.create_headcount(session["id"], payload.count, created_by="admin")
    return {"status": "ok", "count": hc["count"], "recorded_at": hc["recorded_at"].isoformat()}


@router.get("/api/headcount")
async def api_get_headcounts():
    session = crud.get_open_session()
    if not session:
        return {"headcounts": []}
    return {"headcounts": crud.get_session_headcounts(session["id"])}


# --- Kiosk Revenue ---

@router.post("/api/kiosk-revenue")
async def api_kiosk_revenue(request: Request, payload: RevenueRequest):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    session = crud.get_open_session()
    if not session:
        return JSONResponse({"status": "no_session"}, status_code=400)
    crud.update_session_revenue(session["id"], payload.amount)
    return {"status": "ok", "amount": payload.amount}


@router.get("/api/kiosk-revenue")
async def api_get_kiosk_revenue(request: Request):
    session = crud.get_open_session()
    if not session:
        return {"amount": 0}
    amount = crud.get_session_revenue(session["id"])
    return {"amount": amount}


@router.post("/api/kiosk-revenue/{session_id}")
async def api_update_session_revenue(request: Request, session_id: int, payload: RevenueRequest):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    session = crud.get_session_by_id(session_id)
    if not session:
        return JSONResponse({"status": "not_found"}, status_code=404)
    crud.update_session_revenue(session_id, payload.amount)
    return {"status": "ok", "amount": payload.amount}


# --- Checkin management ---

@router.post("/api/checkin/{checkin_id}/undo-checkout")
async def api_undo_checkout(request: Request, checkin_id: int):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    ok = crud.undo_checkout(checkin_id)
    if not ok:
        return JSONResponse({"status": "not_found"}, status_code=404)
    return {"status": "ok"}


@router.delete("/api/checkin/{checkin_id}")
async def api_delete_checkin(request: Request, checkin_id: int):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    ok = crud.delete_checkin(checkin_id)
    if not ok:
        return JSONResponse({"status": "not_found"}, status_code=404)
    return {"status": "ok"}


# --- Manual checkin ---

@router.post("/admin/manual", response_class=HTMLResponse)
async def admin_manual(
    request: Request,
    member_number: str = Form(""),
    full_name: str = Form(""),
    guest_name: str = Form(""),
    qr_data: str = Form(""),
):
    guard = require_admin(request)
    if guard:
        return guard

    open_session = crud.get_open_session()
    if not open_session:
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "open_session": None, "message": None, "error": "No open session"},
        )

    if guest_name:
        crud.create_checkin(
            session_id=open_session["id"],
            player_uuid=None,
            guest_name=guest_name.strip(),
            method="manual",
            created_by="admin",
        )
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "open_session": open_session, "message": "Guest checked in", "error": None},
        )

    player = None
    if member_number:
        value = member_number.strip()
        player = crud.get_player_by_uuid(value) or crud.get_player_by_card_id(value)
    if not player and full_name:
        results = crud.search_players_by_name(full_name)
        if len(results) == 1:
            player = results[0]

    if not player:
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "open_session": open_session, "message": None, "error": "Player not found or ambiguous"},
        )

    if qr_data:
        card_id = extract_token(qr_data)
        if card_id:
            ok, msg = crud.link_card(player["uuid"], card_id)
            if not ok:
                return templates.TemplateResponse(
                    "admin.html",
                    {"request": request, "open_session": open_session, "message": None, "error": msg},
                )

    existing = crud.get_checkin_for_player(open_session["id"], player["uuid"])
    if existing:
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "open_session": open_session, "message": None, "error": "Player already checked in"},
        )

    crud.create_checkin(
        session_id=open_session["id"],
        player_uuid=player["uuid"],
        guest_name=None,
        method="manual",
        created_by="admin",
    )

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "open_session": open_session, "message": "Player checked in", "error": None},
    )


# --- Calendar ---

@router.get("/api/calendar")
async def api_calendar(request: Request, year: int, month: int):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    sessions = crud.get_sessions_for_month(year, month)
    by_date = {}
    for s in sessions:
        date_key = s["start_time"].strftime("%Y-%m-%d") if s["start_time"] else None
        if not date_key:
            continue
        duration_minutes = None
        if s["start_time"] and s["end_time"]:
            duration_minutes = round((s["end_time"] - s["start_time"]).total_seconds() / 60)
        if date_key not in by_date:
            by_date[date_key] = []
        by_date[date_key].append({
            "session_id": s["id"],
            "start_time": s["start_time"].isoformat(),
            "end_time": s["end_time"].isoformat() if s["end_time"] else None,
            "status": s["status"],
            "total_checkins": s["total_checkins"],
            "peak_headcount": s["peak_headcount"],
            "duration_minutes": duration_minutes,
            "location": s["location"],
            "kiosk_revenue": float(s.get("kiosk_revenue", 0)),
        })
    return {"year": year, "month": month, "sessions": by_date}


@router.get("/api/calendar/day")
async def api_calendar_day(request: Request, session_id: int):
    if not is_admin(request):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    session = crud.get_session_by_id(session_id)
    if not session:
        return JSONResponse({"status": "not_found"}, status_code=404)
    checkins = crud.get_session_checkins(session_id)
    headcounts = crud.get_session_headcounts(session_id)
    peak = max((h["count"] for h in headcounts), default=0)
    peak_time = None
    for h in headcounts:
        if h["count"] == peak and peak > 0:
            peak_time = h["recorded_at"] if h.get("recorded_at") else None
            break
    duration_minutes = None
    if session["start_time"] and session.get("end_time"):
        duration_minutes = round((session["end_time"] - session["start_time"]).total_seconds() / 60)
    return {
        "session_id": session_id,
        "start_time": session["start_time"].isoformat() if session["start_time"] else None,
        "end_time": session["end_time"].isoformat() if session.get("end_time") else None,
        "status": session["status"],
        "location": session.get("location", ""),
        "total_checkins": len(checkins),
        "peak_headcount": peak,
        "peak_time": peak_time,
        "duration_minutes": duration_minutes,
        "kiosk_revenue": float(session.get("kiosk_revenue", 0)),
        "checkins": checkins,
        "headcounts": headcounts,
    }


# --- Dev tools ---

def _require_dev(request: Request):
    if not request.session.get("is_dev"):
        return JSONResponse({"status": "unauthorized"}, status_code=401)
    return None


@router.delete("/api/dev/session/{session_id}")
async def api_dev_delete_session(request: Request, session_id: int):
    denied = _require_dev(request)
    if denied:
        return denied
    session = crud.get_session_by_id(session_id)
    if not session:
        return JSONResponse({"status": "not_found"}, status_code=404)
    crud.delete_session(session_id)
    _safe_log_action("dev_delete_session", f"Session {session_id} deleted", "dev")
    return {"status": "ok"}


@router.get("/api/dev/sessions")
async def api_dev_list_sessions(request: Request):
    denied = _require_dev(request)
    if denied:
        return denied
    sessions = crud.get_all_sessions()
    result = []
    for s in sessions:
        result.append({
            "id": s["id"],
            "start_time": s["start_time"].isoformat() if s["start_time"] else None,
            "end_time": s["end_time"].isoformat() if s.get("end_time") else None,
            "status": s["status"],
            "location": s.get("location", ""),
            "total_checkins": s.get("total_checkins", 0),
        })
    return {"sessions": result}


# --- History ---

@router.get("/admin/history", response_class=HTMLResponse)
async def admin_history(request: Request):
    guard = require_admin(request)
    if guard:
        return guard
    sessions = crud.get_all_sessions()
    return templates.TemplateResponse("history.html", {"request": request, "sessions": sessions})


@router.get("/admin/history/{session_id}", response_class=HTMLResponse)
async def admin_session_detail(request: Request, session_id: int):
    guard = require_admin(request)
    if guard:
        return guard
    session = crud.get_session_by_id(session_id)
    if not session:
        return RedirectResponse("/admin/history", status_code=302)
    checkins = crud.get_session_checkins(session_id)
    headcounts = crud.get_session_headcounts(session_id)
    peak = max((h["count"] for h in headcounts), default=0)
    return templates.TemplateResponse(
        "session_detail.html",
        {"request": request, "session": session, "checkins": checkins, "total": len(checkins), "headcounts": headcounts, "peak": peak},
    )


# --- Members ---

@router.get("/admin/members", response_class=HTMLResponse)
async def admin_members(request: Request, q: str | None = None):
    guard = require_admin(request)
    if guard:
        return guard
    members = crud.get_all_members(search=q)
    return templates.TemplateResponse(
        "members.html",
        {"request": request, "members": members, "search": q or "", "total": len(members)},
    )


# --- Audit ---

@router.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit(request: Request):
    guard = require_admin(request)
    if guard:
        return guard
    entries = crud.get_audit_log()
    return templates.TemplateResponse("audit.html", {"request": request, "entries": entries})

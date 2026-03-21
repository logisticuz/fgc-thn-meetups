from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from ..config import settings
from ..deps import templates, is_admin, require_admin, extract_token
from .. import crud

router = APIRouter()


class SessionStart(BaseModel):
    location: str | None = None
    notes: str | None = None


class HeadcountRequest(BaseModel):
    count: int


# --- Auth ---

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(request: Request, pin: str = Form(...)):
    if pin == settings.admin_pin:
        request.session["is_admin"] = True
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid PIN"})


@router.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)


# --- Dashboard ---

@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    guard = require_admin(request)
    if guard:
        return guard
    open_session = crud.get_open_session()
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "open_session": open_session, "message": None, "error": None},
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
    crud.end_session(session["id"])
    crud.log_action("session_ended", f"Session {session['id']} ended", "admin")
    return {"status": "ended"}


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


# --- Checkin management ---

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

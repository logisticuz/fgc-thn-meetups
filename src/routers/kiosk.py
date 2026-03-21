from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from ..deps import templates, extract_token
from .. import crud

router = APIRouter()


class CheckinRequest(BaseModel):
    qr_data: str


class LinkAndCheckinRequest(BaseModel):
    card_id: str
    player_name: str | None = None


@router.get("/")
async def root():
    return RedirectResponse("/kiosk", status_code=302)


@router.get("/kiosk", response_class=HTMLResponse)
async def kiosk(request: Request):
    open_session = crud.get_open_session()
    return templates.TemplateResponse(
        "kiosk.html",
        {"request": request, "open_session": open_session},
    )


@router.get("/api/sessions/open")
async def api_open_session():
    session = crud.get_open_session()
    if not session:
        return {"open": False}
    return {"open": True, "id": session["id"], "start_time": session["start_time"].isoformat()}


@router.post("/api/checkin")
async def api_checkin(payload: CheckinRequest):
    session = crud.get_open_session()
    if not session:
        return JSONResponse({"status": "no_session"})

    token = extract_token(payload.qr_data)
    if not token:
        return JSONResponse({"status": "invalid"})

    player = crud.get_player_by_card_id(token)
    if not player:
        return JSONResponse({"status": "unknown", "card_id": token})

    existing = crud.get_checkin_for_player(session["id"], player["uuid"])
    if existing:
        if existing["checkout_time"] is not None:
            total = crud.count_checkins(session["id"])
            return JSONResponse({"status": "already_left", "member_name": player["name"], "total": total})
        checkout = crud.checkout_player(session["id"], player["uuid"])
        present = crud.count_present(session["id"])
        return JSONResponse({
            "status": "checkout",
            "member_name": player["name"],
            "checkout_time": checkout["checkout_time"].isoformat() if checkout and checkout["checkout_time"] else "",
            "present": present,
        })

    checkin = crud.create_checkin(
        session_id=session["id"],
        player_uuid=player["uuid"],
        guest_name=None,
        method="qr_scan",
    )
    total = crud.count_checkins(session["id"])
    present = crud.count_present(session["id"])
    streak = crud.get_member_streak(player["uuid"]) + 1
    return JSONResponse(
        {
            "status": "ok",
            "member_name": player["name"],
            "checkin_time": checkin["checkin_time"].isoformat(),
            "checkin_number": total,
            "present": present,
            "streak": streak,
        }
    )


@router.get("/api/sessions/attendance")
async def api_session_attendance():
    session = crud.get_open_session()
    if not session:
        return {"open": False, "total": 0, "present": 0, "checkins": []}
    checkins = crud.get_session_checkins(session["id"])
    present = crud.count_present(session["id"])
    return {"open": True, "total": len(checkins), "present": present, "checkins": checkins}


@router.post("/api/link-and-checkin")
async def api_link_and_checkin(payload: LinkAndCheckinRequest):
    session = crud.get_open_session()
    if not session:
        return JSONResponse({"status": "no_session"})

    player = None
    if payload.player_name:
        results = crud.search_players_by_name(payload.player_name)
        if len(results) == 1:
            player = results[0]

    if not player:
        return JSONResponse({"status": "not_found"})

    ok, msg = crud.link_card(player["uuid"], payload.card_id)
    if not ok:
        return JSONResponse({"status": "error", "message": msg})

    existing = crud.get_checkin_for_player(session["id"], player["uuid"])
    if existing:
        total = crud.count_checkins(session["id"])
        return JSONResponse({"status": "already_in", "member_name": player["name"], "total": total})

    checkin = crud.create_checkin(
        session_id=session["id"], player_uuid=player["uuid"], guest_name=None, method="qr_scan"
    )
    total = crud.count_checkins(session["id"])
    present = crud.count_present(session["id"])
    streak = crud.get_member_streak(player["uuid"]) + 1
    return JSONResponse({
        "status": "ok",
        "member_name": player["name"],
        "checkin_number": total,
        "present": present,
        "streak": streak,
    })

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from ..deps import templates, extract_token
from .. import crud, validation, ebas

router = APIRouter()


class CheckinRequest(BaseModel):
    qr_data: str


class LinkAndCheckinRequest(BaseModel):
    card_id: str
    player_name: str | None = None


class GuestCheckinRequest(BaseModel):
    guest_name: str


class GuestRegisterRequest(BaseModel):
    checkin_id: str
    tag: str
    personnummer: str
    telephone: str = ""
    email: str = ""


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


@router.post("/api/guest/checkin")
async def api_guest_checkin(payload: GuestCheckinRequest):
    name = payload.guest_name.strip()
    if not name:
        return JSONResponse({"success": False, "error": "Namn krävs"}, status_code=400)

    session = crud.get_open_session()
    if not session:
        return JSONResponse({"status": "no_session"})

    checkin = crud.create_checkin(
        session_id=session["id"],
        player_uuid=None,
        guest_name=name,
        method="kiosk_guest",
    )
    total = crud.count_checkins(session["id"])
    present = crud.count_present(session["id"])
    return JSONResponse({
        "status": "ok",
        "guest_name": name,
        "checkin_number": total,
        "present": present,
        "checkin_id": checkin["id"],
    })


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


@router.post("/api/guest/register")
async def api_guest_register(payload: GuestRegisterRequest):
    try:
        checkin_id = int(payload.checkin_id)
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "Ogiltigt checkin_id"}, status_code=400)

    tag = validation.sanitize_string(payload.tag, "tag")
    personnummer = validation.sanitize_personnummer(payload.personnummer)
    telephone = validation.sanitize_phone(payload.telephone)
    email = validation.sanitize_string(payload.email, "email")

    if not tag:
        return JSONResponse({"success": False, "error": "Tag krävs"}, status_code=400)

    is_valid, error_message = validation.validate_personnummer(personnummer)
    if not is_valid:
        return JSONResponse({"success": False, "error": error_message}, status_code=400)

    checkin = crud.get_checkin_by_id(checkin_id)
    if not checkin:
        return JSONResponse({"success": False, "error": "Checkin hittades inte"}, status_code=404)

    if not checkin.get("guest_name") or checkin.get("player_uuid"):
        return JSONResponse(
            {"success": False, "error": "Checkin är inte en gästincheckning"},
            status_code=400,
        )

    player = crud.get_player_by_tag(tag)
    if player:
        player_uuid = player["uuid"]
    else:
        created_player = crud.create_player(
            name=checkin["guest_name"],
            tag=tag,
            telephone=telephone,
            email=email,
        )
        player_uuid = created_player["uuid"]

    converted = crud.convert_guest_to_player(checkin_id, player_uuid)
    if not converted:
        return JSONResponse({"success": False, "error": "Kunde inte uppdatera checkin"}, status_code=500)

    ebas_result = await ebas.register_member(
        personnummer=personnummer,
        tag=tag,
        email=email,
        telephone=telephone,
    )
    crud.log_action("guest_registered", f"{tag} registered as member", "system")

    return {
        "success": True,
        "player_uuid": player_uuid,
        "ebas_result": ebas_result,
    }

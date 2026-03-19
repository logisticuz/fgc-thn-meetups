from datetime import datetime, timedelta
import csv
import hashlib
import io
import unicodedata
from pathlib import Path
from fastapi import FastAPI, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from .config import settings
from .db import SessionLocal, Base, engine
from . import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FGC THN Meetups")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class SessionStart(BaseModel):
    location: str | None = None
    notes: str | None = None


class CheckinRequest(BaseModel):
    qr_data: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_header(value: str) -> str:
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace(" ", "_").replace("-", "_")
    return value


def _parse_date(value: str | None):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _extract_token(raw: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if "membership_card" in raw:
        raw = raw.split("?")[0]
        parts = raw.rstrip("/").split("/")
        return parts[-1] if parts else None
    return raw


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def _require_admin(request: Request):
    if not _is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    return None


@app.get("/")
async def root():
    return RedirectResponse("/kiosk", status_code=302)


@app.get("/kiosk", response_class=HTMLResponse)
async def kiosk(request: Request, db: Session = Depends(get_db)):
    open_session = crud.get_open_session(db)
    return templates.TemplateResponse(
        "kiosk.html",
        {
            "request": request,
            "open_session": open_session,
        },
    )


@app.post("/api/sessions/start")
async def api_start_session(payload: SessionStart, db: Session = Depends(get_db)):
    session = crud.start_session(db, payload.location, payload.notes)
    return {"id": session.id, "start_time": session.start_time.isoformat()}


@app.post("/api/sessions/end")
async def api_end_session(db: Session = Depends(get_db)):
    session = crud.get_open_session(db)
    if not session:
        return {"status": "none"}
    crud.end_session(db, session)
    return {"status": "ended"}


@app.get("/api/sessions/open")
async def api_open_session(db: Session = Depends(get_db)):
    session = crud.get_open_session(db)
    if not session:
        return {"open": False}
    return {"open": True, "id": session.id, "start_time": session.start_time.isoformat()}


@app.post("/api/checkin")
async def api_checkin(payload: CheckinRequest, db: Session = Depends(get_db)):
    session = crud.get_open_session(db)
    if not session:
        return JSONResponse({"status": "no_session"})

    token = _extract_token(payload.qr_data)
    if not token:
        return JSONResponse({"status": "invalid"})

    token_hash = _hash_token(token)
    member = crud.get_member_by_token_hash(db, token_hash)
    if not member:
        return JSONResponse({"status": "unknown"})

    existing = crud.get_checkin_for_member(db, session.id, member.id)
    if existing:
        if existing.checkout_time is not None:
            total = crud.count_checkins(db, session.id)
            return JSONResponse({"status": "already_left", "member_name": f"{member.first_name} {member.last_name}", "total": total})
        checkout = crud.checkout_member(db, session.id, member.id)
        present = crud.count_present(db, session.id)
        return JSONResponse({
            "status": "checkout",
            "member_name": f"{member.first_name} {member.last_name}",
            "checkout_time": checkout.checkout_time.isoformat() if checkout else "",
            "present": present,
        })

    checkin = crud.create_checkin(
        db,
        session_id=session.id,
        member_id=member.id,
        guest_name=None,
        method="qr_scan",
    )
    total = crud.count_checkins(db, session.id)
    present = crud.count_present(db, session.id)
    return JSONResponse(
        {
            "status": "ok",
            "member_name": f"{member.first_name} {member.last_name}",
            "checkin_time": checkin.checkin_time.isoformat(),
            "checkin_number": total,
            "present": present,
        }
    )


@app.get("/api/sessions/attendance")
async def api_session_attendance(db: Session = Depends(get_db)):
    session = crud.get_open_session(db)
    if not session:
        return {"open": False, "total": 0, "present": 0, "checkins": []}
    checkins = crud.get_session_checkins(db, session.id)
    present = crud.count_present(db, session.id)
    return {"open": True, "total": len(checkins), "present": present, "checkins": checkins}


class HeadcountRequest(BaseModel):
    count: int


@app.post("/api/headcount")
async def api_headcount(payload: HeadcountRequest, db: Session = Depends(get_db)):
    session = crud.get_open_session(db)
    if not session:
        return JSONResponse({"status": "no_session"})
    hc = crud.create_headcount(db, session.id, payload.count, created_by="admin")
    return {"status": "ok", "count": hc.count, "recorded_at": hc.recorded_at.isoformat()}


@app.get("/api/headcount")
async def api_get_headcounts(db: Session = Depends(get_db)):
    session = crud.get_open_session(db)
    if not session:
        return {"headcounts": []}
    return {"headcounts": crud.get_session_headcounts(db, session.id)}


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(request: Request, pin: str = Form(...)):
    if pin == settings.admin_pin:
        request.session["is_admin"] = True
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid PIN"})


@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    guard = _require_admin(request)
    if guard:
        return guard
    open_session = crud.get_open_session(db)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "open_session": open_session,
            "message": None,
            "error": None,
        },
    )


@app.post("/admin/manual", response_class=HTMLResponse)
async def admin_manual(
    request: Request,
    member_number: str = Form(""),
    full_name: str = Form(""),
    guest_name: str = Form(""),
    qr_data: str = Form(""),
    db: Session = Depends(get_db),
):
    guard = _require_admin(request)
    if guard:
        return guard

    open_session = crud.get_open_session(db)
    if not open_session:
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "open_session": None,
                "message": None,
                "error": "No open session",
            },
        )

    if guest_name:
        crud.create_checkin(
            db,
            session_id=open_session.id,
            member_id=None,
            guest_name=guest_name.strip(),
            method="manual",
            created_by="admin",
        )
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "open_session": open_session,
                "message": "Guest checked in",
                "error": None,
            },
        )

    member = None
    if member_number:
        member = crud.get_member_by_number(db, member_number.strip())
    if not member and full_name:
        results = crud.search_members_by_name(db, full_name)
        if len(results) == 1:
            member = results[0]

    if not member:
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "open_session": open_session,
                "message": None,
                "error": "Member not found or ambiguous",
            },
        )

    if qr_data:
        token = _extract_token(qr_data)
        if token:
            token_hash = _hash_token(token)
            ok, msg = crud.link_token(db, member, token_hash)
            if not ok:
                return templates.TemplateResponse(
                    "admin.html",
                    {
                        "request": request,
                        "open_session": open_session,
                        "message": None,
                        "error": msg,
                    },
                )

    existing = crud.get_checkin_for_member(db, open_session.id, member.id)
    if existing:
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "open_session": open_session,
                "message": None,
                "error": "Member already checked in",
            },
        )

    crud.create_checkin(
        db,
        session_id=open_session.id,
        member_id=member.id,
        guest_name=None,
        method="manual",
        created_by="admin",
    )

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "open_session": open_session,
            "message": "Member checked in",
            "error": None,
        },
    )


@app.get("/admin/history", response_class=HTMLResponse)
async def admin_history(request: Request, db: Session = Depends(get_db)):
    guard = _require_admin(request)
    if guard:
        return guard
    sessions = crud.get_all_sessions(db)
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "sessions": sessions},
    )


@app.get("/admin/history/{session_id}", response_class=HTMLResponse)
async def admin_session_detail(request: Request, session_id: int, db: Session = Depends(get_db)):
    guard = _require_admin(request)
    if guard:
        return guard
    from .models import Session as MeetupSession
    session = db.query(MeetupSession).filter(MeetupSession.id == session_id).first()
    if not session:
        return RedirectResponse("/admin/history", status_code=302)
    checkins = crud.get_session_checkins(db, session_id)
    return templates.TemplateResponse(
        "session_detail.html",
        {"request": request, "session": session, "checkins": checkins, "total": len(checkins)},
    )


@app.get("/admin/import", response_class=HTMLResponse)
async def admin_import(request: Request):
    guard = _require_admin(request)
    if guard:
        return guard
    return templates.TemplateResponse("import.html", {"request": request, "summary": None, "error": None})


@app.post("/admin/import", response_class=HTMLResponse)
async def admin_import_post(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    guard = _require_admin(request)
    if guard:
        return guard

    if not file.filename.lower().endswith(".csv"):
        return templates.TemplateResponse(
            "import.html",
            {"request": request, "summary": None, "error": "Only CSV is supported for now"},
        )

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    header_map = {
        "medlemsnummer": "member_number",
        "member_number": "member_number",
        "fornamn": "first_name",
        "firstname": "first_name",
        "efternamn": "last_name",
        "lastname": "last_name",
        "nick": "display_name",
        "display_name": "display_name",
        "discord_id": "discord_id",
        "discord": "discord_id",
        "intradesdatum": "membership_start",
        "membership_start": "membership_start",
        "uttradesdatum": "membership_end",
        "membership_end": "membership_end",
        "city": "city",
        "ort": "city",
        "postnummer": "zip_code",
        "zip_code": "zip_code",
    }

    added = 0
    updated = 0
    rows = 0

    for row in reader:
        rows += 1
        normalized = {}
        for key, value in row.items():
            if key is None:
                continue
            norm = _normalize_header(key)
            field = header_map.get(norm)
            if not field:
                continue
            normalized[field] = value.strip() if value else ""

        if not normalized.get("first_name") or not normalized.get("last_name"):
            continue

        normalized["membership_start"] = _parse_date(normalized.get("membership_start"))
        normalized["membership_end"] = _parse_date(normalized.get("membership_end"))
        normalized["source"] = "ebas_import"

        created = crud.upsert_member(db, normalized)
        if created:
            added += 1
        else:
            updated += 1

    db.commit()

    summary = {
        "rows": rows,
        "added": added,
        "updated": updated,
    }
    return templates.TemplateResponse("import.html", {"request": request, "summary": summary, "error": None})


@app.get("/admin/export", response_class=HTMLResponse)
async def admin_export(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    preset: str | None = None,
    db: Session = Depends(get_db),
):
    guard = _require_admin(request)
    if guard:
        return guard

    if preset == "last2":
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=60)
        return _export_csv(db, start_date, end_date)

    if start and end:
        start_date = _parse_date(start)
        end_date = _parse_date(end)
        if start_date and end_date:
            return _export_csv(db, start_date, end_date)

    return templates.TemplateResponse("export.html", {"request": request, "error": None})


def _export_csv(db: Session, start_date, end_date):
    from .models import Checkin, Session as MeetupSession, Member

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    rows = (
        db.query(Checkin, MeetupSession, Member)
        .join(MeetupSession, Checkin.session_id == MeetupSession.id)
        .outerjoin(Member, Checkin.member_id == Member.id)
        .filter(MeetupSession.start_time >= start_dt, MeetupSession.start_time <= end_dt)
        .order_by(MeetupSession.start_time.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "session_date",
            "session_start_time",
            "session_end_time",
            "member_number",
            "first_name",
            "last_name",
            "guest_name",
            "checkin_time",
            "method",
        ]
    )

    for checkin, session, member in rows:
        writer.writerow(
            [
                session.start_time.date().isoformat() if session.start_time else "",
                session.start_time.isoformat() if session.start_time else "",
                session.end_time.isoformat() if session.end_time else "",
                member.member_number if member else "",
                member.first_name if member else "",
                member.last_name if member else "",
                checkin.guest_name or "",
                checkin.checkin_time.isoformat() if checkin.checkin_time else "",
                checkin.method,
            ]
        )

    output.seek(0)
    filename = f"fgc_thn_meetups_{start_date.isoformat()}_{end_date.isoformat()}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

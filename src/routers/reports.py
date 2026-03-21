import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse

from ..deps import templates, require_admin, parse_date
from .. import crud

router = APIRouter()


@router.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats(request: Request):
    guard = require_admin(request)
    if guard:
        return guard
    overview = crud.get_overview_stats()
    session_stats = crud.get_session_stats()
    member_stats = crud.get_member_stats()
    return templates.TemplateResponse(
        "stats.html",
        {"request": request, "overview": overview, "session_stats": session_stats, "member_stats": member_stats},
    )


@router.get("/admin/import", response_class=HTMLResponse)
async def admin_import(request: Request):
    guard = require_admin(request)
    if guard:
        return guard
    return templates.TemplateResponse(
        "import.html",
        {
            "request": request,
            "summary": None,
            "error": "Import hanteras i fgt-checkin-system (players + card_ids).",
            "batches": [],
        },
    )


@router.post("/admin/import", response_class=HTMLResponse)
async def admin_import_post(request: Request, file: UploadFile = File(...)):
    guard = require_admin(request)
    if guard:
        return guard
    _ = file
    return templates.TemplateResponse(
        "import.html",
        {
            "request": request,
            "summary": None,
            "error": "Import är flyttad till fgt-checkin-system. Ingen data importerades här.",
            "batches": [],
        },
    )


@router.get("/admin/export", response_class=HTMLResponse)
async def admin_export(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    preset: str | None = None,
):
    guard = require_admin(request)
    if guard:
        return guard

    if preset == "last2":
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=60)
        return _export_csv(start_date, end_date)

    if start and end:
        start_date = parse_date(start)
        end_date = parse_date(end)
        if start_date and end_date:
            return _export_csv(start_date, end_date)

    return templates.TemplateResponse("export.html", {"request": request, "error": None})


def _export_csv(start_date, end_date):
    rows = crud.get_checkins_for_export(start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "session_date",
            "session_start_time",
            "session_end_time",
            "player_uuid",
            "player_name",
            "guest_name",
            "checkin_time",
            "checkout_time",
            "duration_minutes",
            "method",
        ]
    )

    for row in rows:
        duration = ""
        if row["checkin_time"] and row["checkout_time"]:
            dur = (row["checkout_time"] - row["checkin_time"]).total_seconds() / 60
            duration = str(round(dur))

        writer.writerow(
            [
                row["session_start"].date().isoformat() if row["session_start"] else "",
                row["session_start"].isoformat() if row["session_start"] else "",
                row["session_end"].isoformat() if row["session_end"] else "",
                row["player_uuid"] or "",
                row["player_name"] or "",
                row["guest_name"] or "",
                row["checkin_time"].isoformat() if row["checkin_time"] else "",
                row["checkout_time"].isoformat() if row["checkout_time"] else "",
                duration,
                row["method"],
            ]
        )

    output.seek(0)
    filename = f"fgc_thn_meetups_{start_date.isoformat()}_{end_date.isoformat()}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

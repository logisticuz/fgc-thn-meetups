from datetime import datetime
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from .models import Member, Session as MeetupSession, Checkin, Headcount, ImportBatch, AuditLog


def get_open_session(db: Session) -> MeetupSession | None:
    return (
        db.query(MeetupSession)
        .filter(MeetupSession.status == "open")
        .order_by(MeetupSession.start_time.desc())
        .first()
    )


def start_session(db: Session, location: str | None, notes: str | None) -> MeetupSession:
    current = get_open_session(db)
    if current:
        return current
    session = MeetupSession(location=location, notes=notes, status="open")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(db: Session, session: MeetupSession) -> None:
    session.status = "closed"
    session.end_time = datetime.utcnow()
    db.commit()


def get_member_by_token_hash(db: Session, token_hash: str) -> Member | None:
    return db.query(Member).filter(Member.token_hash == token_hash).first()


def get_member_by_number(db: Session, member_number: str) -> Member | None:
    return db.query(Member).filter(Member.member_number == member_number).first()


def search_members_by_name(db: Session, query: str) -> list[Member]:
    q = query.strip().lower()
    if not q:
        return []
    like = f"%{q}%"
    return (
        db.query(Member)
        .filter(or_(func.lower(Member.first_name).like(like), func.lower(Member.last_name).like(like)))
        .limit(10)
        .all()
    )


def link_token(db: Session, member: Member, token_hash: str) -> tuple[bool, str | None]:
    existing = get_member_by_token_hash(db, token_hash)
    if existing and existing.id != member.id:
        return False, "Token already linked to another member"
    member.token_hash = token_hash
    db.commit()
    return True, None


def create_checkin(
    db: Session,
    session_id: int,
    member_id: int | None,
    guest_name: str | None,
    method: str,
    created_by: str | None = None,
) -> Checkin:
    checkin = Checkin(
        session_id=session_id,
        member_id=member_id,
        guest_name=guest_name,
        method=method,
        created_by=created_by,
        checkin_time=datetime.utcnow(),
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


def get_checkin_for_member(db: Session, session_id: int, member_id: int) -> Checkin | None:
    return (
        db.query(Checkin)
        .filter(Checkin.session_id == session_id, Checkin.member_id == member_id)
        .first()
    )


def count_checkins(db: Session, session_id: int) -> int:
    return db.query(Checkin).filter(Checkin.session_id == session_id).count()


def get_session_checkins(db: Session, session_id: int) -> list[dict]:
    rows = (
        db.query(Checkin, Member)
        .outerjoin(Member, Checkin.member_id == Member.id)
        .filter(Checkin.session_id == session_id)
        .order_by(Checkin.checkin_time.asc())
        .all()
    )
    result = []
    for i, (checkin, member) in enumerate(rows, 1):
        result.append({
            "number": i,
            "name": f"{member.first_name} {member.last_name}" if member else checkin.guest_name or "Guest",
            "checkin_time": checkin.checkin_time.isoformat() if checkin.checkin_time else "",
            "checkout_time": checkin.checkout_time.isoformat() if checkin.checkout_time else "",
            "checked_out": checkin.checkout_time is not None,
            "method": checkin.method,
            "checkin_id": checkin.id,
        })
    return result


def checkout_member(db: Session, session_id: int, member_id: int) -> Checkin | None:
    checkin = get_checkin_for_member(db, session_id, member_id)
    if not checkin or checkin.checkout_time is not None:
        return None
    checkin.checkout_time = datetime.utcnow()
    db.commit()
    db.refresh(checkin)
    return checkin


def count_present(db: Session, session_id: int) -> int:
    return (
        db.query(Checkin)
        .filter(Checkin.session_id == session_id, Checkin.checkout_time.is_(None))
        .count()
    )


def create_headcount(db: Session, session_id: int, count: int, created_by: str | None = None) -> Headcount:
    hc = Headcount(
        session_id=session_id,
        count=count,
        created_by=created_by,
    )
    db.add(hc)
    db.commit()
    db.refresh(hc)
    return hc


def get_session_headcounts(db: Session, session_id: int) -> list[dict]:
    rows = (
        db.query(Headcount)
        .filter(Headcount.session_id == session_id)
        .order_by(Headcount.recorded_at.asc())
        .all()
    )
    return [
        {
            "count": hc.count,
            "recorded_at": hc.recorded_at.isoformat() if hc.recorded_at else "",
        }
        for hc in rows
    ]


def get_all_sessions(db: Session) -> list[dict]:
    sessions = (
        db.query(MeetupSession)
        .order_by(MeetupSession.start_time.desc())
        .all()
    )
    result = []
    for s in sessions:
        total = db.query(Checkin).filter(Checkin.session_id == s.id).count()
        result.append({
            "id": s.id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "location": s.location or "",
            "status": s.status,
            "notes": s.notes or "",
            "total_checkins": total,
        })
    return result


def delete_checkin(db: Session, checkin_id: int) -> bool:
    checkin = db.query(Checkin).filter(Checkin.id == checkin_id).first()
    if not checkin:
        return False
    db.delete(checkin)
    db.commit()
    return True


def upsert_member(db: Session, data: dict) -> bool:
    member_number = data.get("member_number")
    member = None
    if member_number:
        member = get_member_by_number(db, member_number)
    if not member:
        member = Member(**data)
        db.add(member)
        return True

    for key, value in data.items():
        if value is None or value == "":
            continue
        if key == "token_hash":
            continue
        setattr(member, key, value)
    return False


# --- Member list ---

def get_all_members(db: Session, search: str | None = None) -> list[Member]:
    q = db.query(Member)
    if search:
        like = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(Member.first_name).like(like),
                func.lower(Member.last_name).like(like),
                func.lower(Member.member_number).like(like),
                func.lower(Member.display_name).like(like),
            )
        )
    return q.order_by(Member.last_name, Member.first_name).all()


# --- Import batch ---

def create_import_batch(db: Session, filename: str, file_hash: str, total: int, added: int, updated: int) -> ImportBatch:
    batch = ImportBatch(
        source_file_name=filename,
        source_file_hash=file_hash,
        records_total=total,
        records_added=added,
        records_updated=updated,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def get_import_batches(db: Session) -> list[ImportBatch]:
    return db.query(ImportBatch).order_by(ImportBatch.imported_at.desc()).all()


# --- Audit log ---

def log_action(db: Session, action: str, detail: str | None = None, created_by: str | None = None) -> None:
    entry = AuditLog(action=action, detail=detail, created_by=created_by)
    db.add(entry)
    db.commit()


def get_audit_log(db: Session, limit: int = 50) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


# --- Statistics ---

def get_session_stats(db: Session, limit: int = 20) -> list[dict]:
    sessions = (
        db.query(MeetupSession)
        .filter(MeetupSession.status == "closed")
        .order_by(MeetupSession.start_time.desc())
        .limit(limit)
        .all()
    )
    result = []
    for s in sessions:
        total = db.query(Checkin).filter(Checkin.session_id == s.id).count()
        peak = db.query(func.max(Headcount.count)).filter(Headcount.session_id == s.id).scalar() or 0
        result.append({
            "date": s.start_time.strftime("%Y-%m-%d") if s.start_time else "",
            "weekday": s.start_time.strftime("%A") if s.start_time else "",
            "total_checkins": total,
            "peak_headcount": peak,
        })
    return result


def get_member_stats(db: Session) -> list[dict]:
    members = db.query(Member).all()
    result = []
    for m in members:
        checkins = db.query(Checkin).filter(Checkin.member_id == m.id).all()
        if not checkins:
            continue
        total_sessions = len(checkins)
        last = max(c.checkin_time for c in checkins if c.checkin_time)
        durations = []
        for c in checkins:
            if c.checkin_time and c.checkout_time:
                dur = (c.checkout_time - c.checkin_time).total_seconds() / 60
                durations.append(dur)
        avg_dur = round(sum(durations) / len(durations)) if durations else None
        result.append({
            "name": f"{m.first_name} {m.last_name}",
            "total_sessions": total_sessions,
            "last_attended": last.strftime("%Y-%m-%d") if last else "",
            "avg_duration_minutes": avg_dur,
        })
    result.sort(key=lambda x: x["total_sessions"], reverse=True)
    return result


def get_overview_stats(db: Session) -> dict:
    total_members = db.query(Member).count()
    total_sessions = db.query(MeetupSession).filter(MeetupSession.status == "closed").count()
    total_checkins = db.query(Checkin).count()
    avg = round(total_checkins / total_sessions, 1) if total_sessions > 0 else 0

    most_active = (
        db.query(Member.first_name, Member.last_name, func.count(Checkin.id).label("cnt"))
        .join(Checkin, Checkin.member_id == Member.id)
        .group_by(Member.id)
        .order_by(func.count(Checkin.id).desc())
        .first()
    )
    most_active_name = f"{most_active[0]} {most_active[1]}" if most_active else "—"

    return {
        "total_members": total_members,
        "total_sessions": total_sessions,
        "total_checkins": total_checkins,
        "avg_per_session": avg,
        "most_active": most_active_name,
    }

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .db import Base


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    token_hash = Column(String, unique=True, nullable=True, index=True)
    member_number = Column(String, unique=True, nullable=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    discord_id = Column(String, nullable=True)
    membership_start = Column(Date, nullable=True)
    membership_end = Column(Date, nullable=True)
    city = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    source = Column(String, nullable=False, default="ebas_import")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    location = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    guest_name = Column(String, nullable=True)
    checkin_time = Column(DateTime(timezone=True), server_default=func.now())
    checkout_time = Column(DateTime(timezone=True), nullable=True)
    method = Column(String, nullable=False, default="qr_scan")
    created_by = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("session_id", "member_id", name="uq_session_member"),
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True)
    source_file_name = Column(String, nullable=False)
    source_file_hash = Column(String, nullable=True)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    records_total = Column(Integer, nullable=False, default=0)
    records_added = Column(Integer, nullable=False, default=0)
    records_updated = Column(Integer, nullable=False, default=0)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Headcount(Base):
    __tablename__ = "headcounts"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    count = Column(Integer, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=True)

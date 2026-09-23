import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DispatchCase(Base):
    __tablename__ = "dispatch_cases"

    case_ref: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    planning_start: Mapped[date] = mapped_column(Date)


class DispatchWorker(Base):
    __tablename__ = "dispatch_workers"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    skills: Mapped[list[str]] = mapped_column(JSONB, default=list)
    zone: Mapped[str] = mapped_column(String(40))
    capacity_hours: Mapped[int] = mapped_column(Integer)
    unavailable_dates: Mapped[list[str]] = mapped_column(JSONB, default=list)


class DispatchJob(Base):
    __tablename__ = "dispatch_jobs"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    case_ref: Mapped[str] = mapped_column(ForeignKey("dispatch_cases.case_ref", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    required_skill: Mapped[str | None] = mapped_column(String(60))
    duration_hours: Mapped[int | None] = mapped_column(Integer)
    deadline: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    zone: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="unassigned", index=True)


class DispatchAssignment(Base):
    __tablename__ = "dispatch_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[str] = mapped_column(ForeignKey("dispatch_jobs.id", ondelete="CASCADE"), unique=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("dispatch_workers.id", ondelete="CASCADE"), index=True)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[int] = mapped_column(Integer)
    source_action_key: Mapped[str | None] = mapped_column(String(200), unique=True)


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    meeting_date: Mapped[date] = mapped_column(Date)
    audio_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="uploaded")
    error: Mapped[str | None] = mapped_column(Text)
    duration_s: Mapped[float | None] = mapped_column(Float)
    language_hint: Mapped[str] = mapped_column(String(16), default="auto")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingSpeaker(Base):
    __tablename__ = "meeting_speakers"

    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True)
    speaker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))


class MeetingSegment(Base):
    __tablename__ = "meeting_segments"
    __table_args__ = (Index("ix_meeting_segments_meeting_idx", "meeting_id", "idx", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(Integer)
    start_s: Mapped[float] = mapped_column(Float)
    end_s: Mapped[float] = mapped_column(Float)
    speaker_id: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    words: Mapped[list[dict]] = mapped_column(JSON, default=list)


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    decisions: Mapped[list[str]] = mapped_column(JSON, default=list)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    protocol_id: Mapped[str] = mapped_column(ForeignKey("protocols.id", ondelete="CASCADE"))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    action_key: Mapped[str] = mapped_column(String(200), unique=True)
    text: Mapped[str] = mapped_column(Text)
    owner_name: Mapped[str] = mapped_column(String(200))
    owner_speaker_id: Mapped[str | None] = mapped_column(String(64))
    deadline_text: Mapped[str] = mapped_column(String(500), default="")
    deadline_date: Mapped[date | None] = mapped_column(Date)
    urgency: Mapped[str] = mapped_column(String(24), default="средний")
    status: Mapped[str] = mapped_column(String(24), default="new")
    source_segment_ids: Mapped[list[int]] = mapped_column(JSON, default=list)

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
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

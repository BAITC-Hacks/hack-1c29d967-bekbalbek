from dataclasses import asdict
from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts import CaseNotFound
from app.domain.models import (
    DispatchAssignment,
    DispatchCase,
    DispatchJob,
    DispatchWorker,
    Meeting,
    MeetingSegment,
    MeetingSpeaker,
)

if TYPE_CHECKING:
    from app.speech.align import SpokenSegment
from app.domain.records import AssignmentRecord, JobRecord, PlanContext, WorkerRecord, build_plan_context
from app.domain.schemas import CaseInput

HORIZON_DAYS = 7


def horizon(planning_start: date) -> list[date]:
    return [planning_start + timedelta(days=i) for i in range(HORIZON_DAYS)]


def worker_to_record(row: DispatchWorker) -> WorkerRecord:
    return WorkerRecord(
        id=row.id,
        name=row.name,
        skills=list(row.skills),
        zone=row.zone,
        capacity_hours=row.capacity_hours,
        unavailable_dates=[date.fromisoformat(d) for d in row.unavailable_dates],
    )


def job_to_record(row: DispatchJob) -> JobRecord:
    return JobRecord(
        id=row.id,
        title=row.title,
        required_skill=row.required_skill,
        duration_hours=row.duration_hours,
        deadline=row.deadline,
        priority=row.priority,
        zone=row.zone,
        status=row.status,
    )


def assignment_to_record(row: DispatchAssignment) -> AssignmentRecord:
    return AssignmentRecord(
        id=str(row.id),
        job_id=row.job_id,
        worker_id=row.worker_id,
        scheduled_date=row.scheduled_date,
        hours=row.hours,
        source_action_key=row.source_action_key,
    )


async def get_case_row(session: AsyncSession, case_ref: str) -> DispatchCase:
    row = await session.get(DispatchCase, case_ref)
    if row is None:
        raise CaseNotFound(f"Unknown case '{case_ref}'")
    return row


async def list_workers(session: AsyncSession) -> list[WorkerRecord]:
    rows = await session.execute(select(DispatchWorker).order_by(DispatchWorker.id))
    return [worker_to_record(r) for r in rows.scalars()]


async def list_jobs(session: AsyncSession, case_ref: str) -> list[JobRecord]:
    rows = await session.execute(select(DispatchJob).where(DispatchJob.case_ref == case_ref).order_by(DispatchJob.id))
    return [job_to_record(r) for r in rows.scalars()]


async def list_assignments(session: AsyncSession, start: date, end: date) -> list[AssignmentRecord]:
    rows = await session.execute(
        select(DispatchAssignment)
        .where(DispatchAssignment.scheduled_date >= start, DispatchAssignment.scheduled_date <= end)
        .order_by(DispatchAssignment.scheduled_date, DispatchAssignment.worker_id, DispatchAssignment.job_id)
    )
    return [assignment_to_record(r) for r in rows.scalars()]


async def load_plan_context(session: AsyncSession, case_ref: str, case_input: CaseInput) -> PlanContext:
    await get_case_row(session, case_ref)
    days = horizon(case_input.planning_start)
    return build_plan_context(
        case_input,
        workers=await list_workers(session),
        jobs=await list_jobs(session, case_ref),
        assignments=await list_assignments(session, days[0], days[-1]),
    )


async def get_meeting(session: AsyncSession, meeting_id: str) -> Meeting:
    row = await session.get(Meeting, meeting_id)
    if row is None:
        raise CaseNotFound(f"Unknown meeting '{meeting_id}'")
    return row


async def list_segments(session: AsyncSession, meeting_id: str) -> list[MeetingSegment]:
    rows = await session.scalars(
        select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id).order_by(MeetingSegment.idx)
    )
    return list(rows)


async def list_speakers(session: AsyncSession, meeting_id: str) -> list[MeetingSpeaker]:
    rows = await session.scalars(
        select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id).order_by(MeetingSpeaker.speaker_id)
    )
    return list(rows)


async def replace_transcript(
    session: AsyncSession, meeting_id: str, segments: list["SpokenSegment"], duration_s: float
) -> None:
    meeting = await get_meeting(session, meeting_id)
    await session.execute(delete(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id))
    await session.execute(delete(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id))
    for idx, segment in enumerate(segments):
        session.add(
            MeetingSegment(
                meeting_id=meeting_id,
                idx=idx,
                start_s=segment.start,
                end_s=segment.end,
                speaker_id=segment.speaker,
                language=segment.language,
                text=segment.text,
                words=[asdict(word) for word in segment.words],
            )
        )
    for speaker in sorted({segment.speaker for segment in segments}):
        session.add(MeetingSpeaker(meeting_id=meeting_id, speaker_id=speaker, display_name=speaker))
    meeting.duration_s = duration_s
    await session.flush()


async def set_status(session: AsyncSession, meeting_id: str, status: str, error: str | None = None) -> None:
    meeting = await get_meeting(session, meeting_id)
    meeting.status, meeting.error = status, error
    await session.flush()

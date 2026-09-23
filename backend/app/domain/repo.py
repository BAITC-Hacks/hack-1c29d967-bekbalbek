from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts import CaseNotFound
from app.domain.models import DispatchAssignment, DispatchCase, DispatchJob, DispatchWorker
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

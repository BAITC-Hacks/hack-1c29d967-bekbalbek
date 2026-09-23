from dataclasses import dataclass, field, replace
from datetime import date

from app.domain.schemas import CaseInput, JobStatus, Priority


@dataclass(frozen=True)
class WorkerRecord:
    id: str
    name: str
    skills: list[str]
    zone: str
    capacity_hours: int
    unavailable_dates: list[date]


@dataclass(frozen=True)
class JobRecord:
    id: str
    title: str
    required_skill: str | None
    duration_hours: int | None
    deadline: date
    priority: Priority
    zone: str
    status: JobStatus


@dataclass(frozen=True)
class AssignmentRecord:
    id: str
    job_id: str
    worker_id: str
    scheduled_date: date
    hours: int
    source_action_key: str | None = None


@dataclass(frozen=True)
class PlanContext:
    planning_start: date
    workers: dict[str, WorkerRecord]
    jobs: dict[str, JobRecord]
    assignments: list[AssignmentRecord]
    requested_job_ids: list[str] = field(default_factory=list)


def apply_job_overrides(job: JobRecord, case_input: CaseInput) -> JobRecord:
    override = case_input.job_overrides.get(job.id)
    if override is None:
        return job
    return replace(
        job,
        required_skill=override.required_skill if override.required_skill is not None else job.required_skill,
        duration_hours=override.duration_hours if override.duration_hours is not None else job.duration_hours,
    )


def apply_capacity_override(worker: WorkerRecord, case_input: CaseInput) -> WorkerRecord:
    capacity = case_input.capacity_overrides.get(worker.id)
    return worker if capacity is None else replace(worker, capacity_hours=capacity)


def build_plan_context(
    case_input: CaseInput,
    *,
    workers: list[WorkerRecord],
    jobs: list[JobRecord],
    assignments: list[AssignmentRecord],
) -> PlanContext:
    effective_jobs = {j.id: apply_job_overrides(j, case_input) for j in jobs}
    effective_workers = {w.id: apply_capacity_override(w, case_input) for w in workers}
    unassigned = [j.id for j in effective_jobs.values() if j.status == "unassigned"]
    requested = [j for j in case_input.job_ids if j in effective_jobs] if case_input.job_ids else unassigned
    return PlanContext(
        planning_start=case_input.planning_start,
        workers=effective_workers,
        jobs=effective_jobs,
        assignments=list(assignments),
        requested_job_ids=requested,
    )

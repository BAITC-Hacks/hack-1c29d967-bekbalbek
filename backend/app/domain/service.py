import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts import ActionResult, ExecutionError, ValidationReport, VerificationCheck, VerificationReport
from app.core.serialization import jsonable
from app.domain.models import DispatchAssignment, DispatchJob, DispatchWorker
from app.domain.records import apply_job_overrides
from app.domain.repo import (
    get_case_row,
    horizon,
    job_to_record,
    list_assignments,
    list_jobs,
    list_workers,
    load_plan_context,
)
from app.domain.rules import RULES, evaluate_plan, load_by_worker_day
from app.domain.schemas import CaseInput, DispatchProposal


def rules_as_dicts() -> list[dict[str, str]]:
    return [
        {"id": r.id, "label": r.label, "severity": r.severity, "source": r.source, "description": r.description}
        for r in RULES.values()
    ]


async def load_case_view(session: AsyncSession, case_ref: str) -> dict[str, Any]:
    case = await get_case_row(session, case_ref)
    days = horizon(case.planning_start)
    return jsonable(
        {
            "case_ref": case.case_ref,
            "title": case.title,
            "description": case.description,
            "planning_start": case.planning_start,
            "dates": days,
            "workers": await list_workers(session),
            "jobs": await list_jobs(session, case_ref),
            "assignments": [jsonable(a) for a in await list_assignments(session, days[0], days[-1])],
            "rules": rules_as_dicts(),
        }
    )


async def validate_proposal(
    session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: DispatchProposal
) -> ValidationReport:
    ctx = await load_plan_context(session, case_ref, case_input)
    return evaluate_plan(ctx, proposal.actions)


async def fingerprint(session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: DispatchProposal) -> str:
    ctx = await load_plan_context(session, case_ref, case_input)
    basis = {
        "workers": sorted(jsonable(list(ctx.workers.values())), key=lambda w: w["id"]),
        "jobs": sorted(jsonable(list(ctx.jobs.values())), key=lambda j: j["id"]),
        "assignments": sorted(
            jsonable(ctx.assignments), key=lambda a: (a["worker_id"], a["scheduled_date"], a["job_id"])
        ),
    }
    return hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()


async def snapshot(session: AsyncSession, case_ref: str, case_input: CaseInput) -> dict[str, Any]:
    ctx = await load_plan_context(session, case_ref, case_input)
    load = load_by_worker_day(ctx, [])
    return jsonable(
        {
            "planning_start": ctx.planning_start,
            "workers": [
                {"id": w.id, "name": w.name, "capacity_hours": w.capacity_hours, "load_by_date": load.get(w.id, {})}
                for w in ctx.workers.values()
            ],
            "assignments": ctx.assignments,
            "jobs": [{"id": j.id, "status": j.status} for j in ctx.jobs.values()],
        }
    )


async def execute_actions(
    session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: DispatchProposal, action_keys: dict[str, str]
) -> list[ActionResult]:
    await get_case_row(session, case_ref)
    results: list[ActionResult] = []
    for action in proposal.actions:
        job = await session.get(DispatchJob, action.job_id, with_for_update=True)
        worker = await session.get(DispatchWorker, action.worker_id)
        if job is None or worker is None:
            raise ExecutionError("record_missing", f"Job {action.job_id} or worker {action.worker_id} no longer exists")
        if job.status != "unassigned":
            raise ExecutionError("job_not_unassigned", f"Job {job.id} is already {job.status}")
        effective = apply_job_overrides(job_to_record(job), case_input)
        if effective.required_skill is None or effective.duration_hours is None:
            raise ExecutionError("job_incomplete", f"Job {job.id} is missing required_skill or duration_hours")
        job.required_skill = effective.required_skill
        job.duration_hours = effective.duration_hours
        job.status = "assigned"
        session.add(
            DispatchAssignment(
                job_id=job.id,
                worker_id=worker.id,
                scheduled_date=action.scheduled_date,
                hours=effective.duration_hours,
                source_action_key=action_keys[action.action_id],
            )
        )
        await session.flush()
        results.append(
            ActionResult(
                action_id=action.action_id,
                type=action.type,
                summary=f"{job.id} → {worker.name} on {action.scheduled_date.isoformat()} ({effective.duration_hours}h)",
                result={
                    "job_id": job.id,
                    "worker_id": worker.id,
                    "scheduled_date": action.scheduled_date.isoformat(),
                    "hours": effective.duration_hours,
                    "action_key": action_keys[action.action_id],
                },
            )
        )
    return results


async def verify_outcome(
    session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: DispatchProposal, results: list[ActionResult]
) -> VerificationReport:
    checks: list[VerificationCheck] = []
    for action in proposal.actions:
        row = (
            await session.execute(select(DispatchAssignment).where(DispatchAssignment.job_id == action.job_id))
        ).scalar_one_or_none()
        job = await session.get(DispatchJob, action.job_id)
        recorded = row is not None and row.worker_id == action.worker_id and row.scheduled_date == action.scheduled_date
        checks.append(
            VerificationCheck(
                id=f"assignment_recorded:{action.action_id}",
                label=f"{action.job_id} assignment stored",
                ok=recorded,
                detail=(
                    f"{action.job_id} → {row.worker_id} on {row.scheduled_date} ({row.hours}h) found in dispatch_assignments"
                    if recorded
                    else f"No matching assignment for {action.job_id} → {action.worker_id} on {action.scheduled_date}"
                ),
            )
        )
        checks.append(
            VerificationCheck(
                id=f"job_status:{action.action_id}",
                label=f"{action.job_id} marked assigned",
                ok=job is not None and job.status == "assigned",
                detail=f"status = {job.status}" if job else "job missing",
            )
        )
    ctx = await load_plan_context(session, case_ref, case_input)
    load = load_by_worker_day(ctx, [])
    touched = {(a.worker_id, a.scheduled_date.isoformat()) for a in proposal.actions}
    over = [
        f"{w} on {d}: {load.get(w, {}).get(d, 0)}h > {ctx.workers[w].capacity_hours}h"
        for w, d in sorted(touched)
        if w in ctx.workers and load.get(w, {}).get(d, 0) > ctx.workers[w].capacity_hours
    ]
    checks.append(
        VerificationCheck(
            id="capacity_respected",
            label="Committed load within capacity",
            ok=not over,
            detail="; ".join(over) if over else "No worker exceeds daily capacity after the change",
        )
    )
    stored = sum(1 for c in checks if c.id.startswith("assignment_recorded:") and c.ok)
    summary = f"{stored} of {len(proposal.actions)} assignment(s) confirmed in the database"
    summary += "; capacity respected" if not over else "; capacity violated"
    return VerificationReport.from_checks(checks, summary)

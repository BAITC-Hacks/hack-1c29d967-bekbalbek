from datetime import date
from typing import Any

from agents import RunContextWrapper

from app.core.context import RunContext
from app.core.contracts import ToolError, ToolSpec
from app.core.serialization import jsonable
from app.domain.records import PlanContext
from app.domain.repo import get_case_row, horizon, load_plan_context
from app.domain.rules import load_by_worker_day, simulate
from app.domain.schemas import AssignJobAction
from app.domain.service import rules_as_dicts

MAX_WORKERS_RETURNED = 50
MAX_JOBS_RETURNED = 50


async def _plan(ctx: RunContextWrapper[RunContext]) -> PlanContext:
    run_ctx = ctx.context
    async with run_ctx.session_factory() as session:
        return await load_plan_context(session, run_ctx.case_ref, run_ctx.case_input)


async def get_case(ctx: RunContextWrapper[RunContext]) -> dict[str, Any]:
    """Read the case: planning start, the jobs to schedule (with user overrides applied), existing assignments and jobs that lack data. Call this first."""
    run_ctx = ctx.context
    async with run_ctx.session_factory() as session:
        case = await get_case_row(session, run_ctx.case_ref)
        plan = await load_plan_context(session, run_ctx.case_ref, run_ctx.case_input)
    requested = [plan.jobs[j] for j in plan.requested_job_ids][:MAX_JOBS_RETURNED]
    days = horizon(plan.planning_start)
    return jsonable(
        {
            "case_ref": case.case_ref,
            "title": case.title,
            "planning_start": plan.planning_start,
            "horizon_end": days[-1],
            "jobs": requested,
            "incomplete_jobs": [j.id for j in requested if j.required_skill is None or j.duration_hours is None],
            "existing_assignments": plan.assignments,
            "notes": run_ctx.case_input.notes,
        }
    )


async def find_resources(ctx: RunContextWrapper[RunContext], skill: str | None, on_date: str | None) -> dict[str, Any]:
    """List workers with remaining capacity per day in the planning horizon, their zone and unavailable dates. Filter by a skill and/or one ISO date (YYYY-MM-DD)."""
    plan = await _plan(ctx)
    days = horizon(plan.planning_start)
    if on_date is not None:
        try:
            days = [date.fromisoformat(on_date)]
        except ValueError as exc:
            raise ToolError("invalid_arguments", f"on_date must be YYYY-MM-DD, got {on_date!r}") from exc
    load = load_by_worker_day(plan, [])
    workers = [w for w in plan.workers.values() if skill is None or skill in w.skills][:MAX_WORKERS_RETURNED]
    return jsonable(
        {
            "skill": skill,
            "workers": [
                {
                    "id": w.id,
                    "name": w.name,
                    "skills": w.skills,
                    "zone": w.zone,
                    "capacity_hours": w.capacity_hours,
                    "unavailable_dates": w.unavailable_dates,
                    "remaining_by_date": {
                        d.isoformat(): 0
                        if d in w.unavailable_dates
                        else max(w.capacity_hours - load.get(w.id, {}).get(d.isoformat(), 0), 0)
                        for d in days
                    },
                }
                for w in workers
            ],
        }
    )


async def lookup_rules(ctx: RunContextWrapper[RunContext]) -> dict[str, Any]:
    """Return the business rules a plan must satisfy, each with its severity (fail blocks the plan, warn is allowed) and source identifier."""
    return {"rules": rules_as_dicts()}


async def simulate_plan(ctx: RunContextWrapper[RunContext], actions: list[AssignJobAction]) -> dict[str, Any]:
    """Check a candidate plan against every rule and compute the resulting load per worker and day. Use it before finalizing and fix every failing check."""
    plan = await _plan(ctx)
    result = simulate(plan, actions)
    issues = [c for c in result.report.checks if c.status != "pass"]
    return jsonable(
        {
            "feasible": result.feasible,
            "failed_rule_ids": result.failed_rule_ids,
            "issues": issues,
            "passed_checks": len(result.report.checks) - len(issues),
            "load": result.load,
        }
    )


TOOLS: list[ToolSpec] = [
    ToolSpec(name="get_case", label="Reading the case", fn=get_case),
    ToolSpec(name="find_resources", label="Checking available workers", fn=find_resources),
    ToolSpec(name="lookup_rules", label="Looking up the rules", fn=lookup_rules),
    ToolSpec(name="simulate_plan", label="Simulating the plan", fn=simulate_plan),
]

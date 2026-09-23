from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import DispatchAssignment, DispatchJob, DispatchWorker

GOAL = "Assign every open job for this week to a qualified technician without breaking capacity, deadline or availability rules."
START = {"planning_start": "2026-09-24"}


async def assignment_count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(DispatchAssignment))).scalar_one()


async def all_case_jobs_assigned(session: AsyncSession, case_ref: str) -> bool:
    rows = (await session.execute(select(DispatchJob.status).where(DispatchJob.case_ref == case_ref))).scalars().all()
    return bool(rows) and all(s == "assigned" for s in rows)


async def make_chen_unavailable(session: AsyncSession) -> None:
    chen = await session.get(DispatchWorker, "w-chen")
    chen.unavailable_dates = [*chen.unavailable_dates, "2026-09-24"]


async def state_unchanged(session: AsyncSession, case_ref: str) -> bool:
    return await assignment_count(session) == 2


async def state_fully_applied(session: AsyncSession, case_ref: str) -> bool:
    return await assignment_count(session) == 8 and await all_case_jobs_assigned(session, case_ref)


async def chen_within_four_hours(session: AsyncSession, case_ref: str) -> bool:
    rows = (
        (await session.execute(select(DispatchAssignment).where(DispatchAssignment.worker_id == "w-chen")))
        .scalars()
        .all()
    )
    per_day: dict[str, int] = {}
    for row in rows:
        per_day[row.scheduled_date.isoformat()] = per_day.get(row.scheduled_date.isoformat(), 0) + row.hours
    return await state_fully_applied(session, case_ref) and all(h <= 4 for h in per_day.values())


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    case_ref: str
    input: dict[str, Any]
    script: str
    expected_status: str
    expected_outcome: str | None
    apply: bool = False
    apply_twice: bool = False
    before_apply: Callable[[AsyncSession], Awaitable[None]] | None = None
    expected_apply_error: str | None = None
    expected_run_error: str | None = None
    expect_event: str | None = None
    final_state_ok: Callable[[AsyncSession, str], Awaitable[bool]] = state_unchanged
    goal: str = GOAL
    options: dict[str, Any] = field(default_factory=dict)


SCENARIOS: list[Scenario] = [
    Scenario(
        "normal_success",
        "Full week plan, applied once, verified in the database",
        "case-dispatch-001",
        START,
        "happy",
        expected_status="verified",
        expected_outcome="proposal_ready",
        apply=True,
        final_state_ok=state_fully_applied,
    ),
    Scenario(
        "missing_information",
        "A job without a required skill must yield needs_input with the exact field",
        "case-dispatch-002",
        START,
        "needs_input",
        expected_status="needs_input",
        expected_outcome="needs_input",
        goal="Schedule the two clinic jobs.",
    ),
    Scenario(
        "impossible_constraints",
        "No welder and no capacity: the agent must report the blocking rules",
        "case-dispatch-003",
        START,
        "infeasible",
        expected_status="infeasible",
        expected_outcome="infeasible",
        goal="Schedule both emergency jobs today.",
    ),
    Scenario(
        "tool_failure",
        "A tool call fails with a structured error; the run still completes",
        "case-dispatch-001",
        START,
        "tool_failure",
        expected_status="proposed",
        expected_outcome="proposal_ready",
        expect_event="tool_failed",
    ),
    Scenario(
        "changed_resource_availability",
        "Chen limited to 4h/day: plan must move his 5h job and still apply cleanly",
        "case-dispatch-001",
        {**START, "capacity_overrides": {"w-chen": 4}},
        "reduced_capacity",
        expected_status="verified",
        expected_outcome="proposal_ready",
        apply=True,
        final_state_ok=chen_within_four_hours,
    ),
    Scenario(
        "duplicate_apply",
        "Applying the same proposal twice writes once and rejects the second request",
        "case-dispatch-001",
        START,
        "happy",
        expected_status="verified",
        expected_outcome="proposal_ready",
        apply=True,
        apply_twice=True,
        expected_apply_error="duplicate_apply",
        final_state_ok=state_fully_applied,
    ),
    Scenario(
        "stale_proposal",
        "Data changes between proposal and apply: the apply must be rejected and nothing written",
        "case-dispatch-001",
        START,
        "happy",
        expected_status="proposed",
        expected_outcome="proposal_ready",
        apply=True,
        before_apply=make_chen_unavailable,
        expected_apply_error="stale_proposal",
        final_state_ok=state_unchanged,
    ),
    Scenario(
        "bounded_revision",
        "First proposal breaks a rule; the single allowed revision fixes it",
        "case-dispatch-001",
        START,
        "revision",
        expected_status="proposed",
        expected_outcome="proposal_ready",
        expect_event="revision_started",
    ),
    Scenario(
        "model_failure",
        "The model provider raises: the run ends in a clear failed state",
        "case-dispatch-001",
        START,
        "model_error",
        expected_status="failed",
        expected_outcome=None,
        expected_run_error="agent_error",
    ),
]

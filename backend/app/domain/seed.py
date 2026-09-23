from datetime import date

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import DispatchAssignment, DispatchCase, DispatchJob, DispatchWorker

# SAMPLE DATA — deterministic fixture for demos and evals, not real operations data.
PLANNING_START = date(2026, 9, 24)

WORKERS = [
    dict(
        id="w-ana",
        name="Ana Petrova",
        skills=["electrical", "hvac"],
        zone="north",
        capacity_hours=8,
        unavailable_dates=[],
    ),
    dict(id="w-boris", name="Boris Kim", skills=["plumbing"], zone="south", capacity_hours=6, unavailable_dates=[]),
    dict(
        id="w-chen",
        name="Chen Wu",
        skills=["electrical", "plumbing"],
        zone="north",
        capacity_hours=8,
        unavailable_dates=["2026-09-25"],
    ),
    dict(id="w-dina", name="Dina Ahmed", skills=["hvac"], zone="south", capacity_hours=4, unavailable_dates=[]),
]

CASES = [
    dict(
        case_ref="case-dispatch-001",
        title="Open jobs for the week of 24 Sep",
        planning_start=PLANNING_START,
        description="Six unassigned jobs across two zones. Two jobs are already scheduled and consume capacity.",
    ),
    dict(
        case_ref="case-dispatch-002",
        title="Job with an unknown skill",
        planning_start=PLANNING_START,
        description="One job arrived without a required skill. The agent must ask for it instead of guessing.",
    ),
    dict(
        case_ref="case-dispatch-003",
        title="Jobs nobody can take",
        planning_start=PLANNING_START,
        description="A welding job with no qualified worker and an HVAC job that exceeds everyone's remaining capacity.",
    ),
]

JOBS = [
    dict(
        id="j-101",
        case_ref="case-dispatch-001",
        title="Replace breaker panel",
        required_skill="electrical",
        duration_hours=3,
        deadline=date(2026, 9, 24),
        priority="high",
        zone="north",
        status="unassigned",
    ),
    dict(
        id="j-102",
        case_ref="case-dispatch-001",
        title="Service rooftop HVAC unit",
        required_skill="hvac",
        duration_hours=4,
        deadline=date(2026, 9, 25),
        priority="normal",
        zone="north",
        status="unassigned",
    ),
    dict(
        id="j-103",
        case_ref="case-dispatch-001",
        title="Fix leaking valve",
        required_skill="plumbing",
        duration_hours=2,
        deadline=date(2026, 9, 24),
        priority="high",
        zone="south",
        status="unassigned",
    ),
    dict(
        id="j-104",
        case_ref="case-dispatch-001",
        title="Install EV charger",
        required_skill="electrical",
        duration_hours=5,
        deadline=date(2026, 9, 26),
        priority="normal",
        zone="south",
        status="unassigned",
    ),
    dict(
        id="j-105",
        case_ref="case-dispatch-001",
        title="Restore cooling in server room",
        required_skill="hvac",
        duration_hours=3,
        deadline=date(2026, 9, 24),
        priority="high",
        zone="south",
        status="unassigned",
    ),
    dict(
        id="j-106",
        case_ref="case-dispatch-001",
        title="Re-pipe utility room",
        required_skill="plumbing",
        duration_hours=6,
        deadline=date(2026, 9, 25),
        priority="low",
        zone="south",
        status="unassigned",
    ),
    dict(
        id="j-201",
        case_ref="case-dispatch-001",
        title="Rewire warehouse lighting",
        required_skill="electrical",
        duration_hours=4,
        deadline=date(2026, 9, 24),
        priority="normal",
        zone="north",
        status="assigned",
    ),
    dict(
        id="j-202",
        case_ref="case-dispatch-001",
        title="Thermostat calibration",
        required_skill="hvac",
        duration_hours=2,
        deadline=date(2026, 9, 24),
        priority="low",
        zone="south",
        status="assigned",
    ),
    dict(
        id="j-107",
        case_ref="case-dispatch-002",
        title="Inspect mystery fault at clinic",
        required_skill=None,
        duration_hours=2,
        deadline=date(2026, 9, 25),
        priority="high",
        zone="north",
        status="unassigned",
    ),
    dict(
        id="j-108",
        case_ref="case-dispatch-002",
        title="Replace outlet strip",
        required_skill="electrical",
        duration_hours=2,
        deadline=date(2026, 9, 25),
        priority="normal",
        zone="north",
        status="unassigned",
    ),
    dict(
        id="j-109",
        case_ref="case-dispatch-003",
        title="Weld broken gate hinge",
        required_skill="welding",
        duration_hours=3,
        deadline=date(2026, 9, 24),
        priority="high",
        zone="north",
        status="unassigned",
    ),
    dict(
        id="j-110",
        case_ref="case-dispatch-003",
        title="Emergency chiller repair",
        required_skill="hvac",
        duration_hours=6,
        deadline=date(2026, 9, 24),
        priority="high",
        zone="south",
        status="unassigned",
    ),
]

ASSIGNMENTS = [
    dict(job_id="j-201", worker_id="w-ana", scheduled_date=date(2026, 9, 24), hours=4, source_action_key=None),
    dict(job_id="j-202", worker_id="w-dina", scheduled_date=date(2026, 9, 24), hours=2, source_action_key=None),
]


async def seed(session: AsyncSession) -> dict[str, int]:
    for table in (DispatchAssignment, DispatchJob, DispatchCase, DispatchWorker):
        await session.execute(delete(table))
    session.add_all([DispatchWorker(**w) for w in WORKERS])
    session.add_all([DispatchCase(**c) for c in CASES])
    await session.flush()
    session.add_all([DispatchJob(**j) for j in JOBS])
    await session.flush()
    session.add_all([DispatchAssignment(**a) for a in ASSIGNMENTS])
    await session.flush()
    return {"workers": len(WORKERS), "cases": len(CASES), "jobs": len(JOBS), "assignments": len(ASSIGNMENTS)}

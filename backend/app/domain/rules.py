from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from app.core.contracts import ValidationCheck, ValidationReport
from app.domain.records import PlanContext
from app.domain.schemas import AssignJobAction


@dataclass(frozen=True)
class Rule:
    id: str
    label: str
    severity: Literal["fail", "warn"]
    source: str
    description: str


RULES: dict[str, Rule] = {
    r.id: r
    for r in [
        Rule(
            "record_exists",
            "Referenced records exist",
            "fail",
            "system:integrity",
            "Every job and worker id must exist in the case.",
        ),
        Rule(
            "job_unassigned",
            "Job is still unassigned",
            "fail",
            "system:integrity",
            "Only unassigned jobs can be scheduled.",
        ),
        Rule(
            "unique_job", "Each job planned once", "fail", "system:integrity", "A job may appear in at most one action."
        ),
        Rule(
            "job_data_complete",
            "Job data is complete",
            "fail",
            "system:integrity",
            "Skill and duration must be known before scheduling.",
        ),
        Rule(
            "skill_match",
            "Skill matches",
            "fail",
            "policy:staffing#skills",
            "The worker must hold the job's required skill.",
        ),
        Rule(
            "daily_capacity",
            "Daily capacity respected",
            "fail",
            "policy:labor#daily-capacity",
            "Hours per worker per day must not exceed capacity, including existing assignments.",
        ),
        Rule(
            "deadline",
            "Scheduled by the deadline",
            "fail",
            "sla:customer#deadline",
            "The scheduled date must be on or before the job deadline.",
        ),
        Rule(
            "availability",
            "Worker available",
            "fail",
            "hr:calendar#unavailability",
            "A worker cannot be scheduled on a date they are marked unavailable.",
        ),
        Rule(
            "not_before_start",
            "Not before planning start",
            "fail",
            "ops:planning#horizon",
            "Nothing is scheduled before the planning start date.",
        ),
        Rule(
            "zone_match",
            "Same zone",
            "warn",
            "ops:routing#zones",
            "Cross-zone assignments are allowed but add travel time.",
        ),
        Rule(
            "plan_completeness",
            "All requested jobs planned",
            "warn",
            "ops:planning#coverage",
            "Requested jobs that stay unplanned are reported.",
        ),
    ]
}


def _check(
    rule_id: str,
    status: Literal["pass", "warn", "fail"],
    message: str,
    action_id: str | None = None,
    refs: list[str] | None = None,
) -> ValidationCheck:
    rule = RULES[rule_id]
    return ValidationCheck(
        rule_id=rule.id,
        label=rule.label,
        status=status,
        message=message,
        action_id=action_id,
        refs=refs or [],
        source=rule.source,
    )


def _verdict(rule_id: str, ok: bool) -> Literal["pass", "warn", "fail"]:
    return "pass" if ok else RULES[rule_id].severity


def _action_checks(ctx: PlanContext, action: AssignJobAction) -> list[ValidationCheck]:
    job = ctx.jobs.get(action.job_id)
    worker = ctx.workers.get(action.worker_id)
    refs = [f"job:{action.job_id}", f"worker:{action.worker_id}"]
    if job is None or worker is None:
        missing = [
            r for r, rec in ((f"job:{action.job_id}", job), (f"worker:{action.worker_id}", worker)) if rec is None
        ]
        return [_check("record_exists", "fail", f"Unknown record(s): {', '.join(missing)}", action.action_id, refs)]
    checks = [_check("record_exists", "pass", "Job and worker exist", action.action_id, refs)]
    checks.append(
        _check(
            "job_unassigned",
            _verdict("job_unassigned", job.status == "unassigned"),
            f"{job.id} is {job.status}",
            action.action_id,
            refs,
        )
    )
    complete = job.required_skill is not None and job.duration_hours is not None
    checks.append(
        _check(
            "job_data_complete",
            _verdict("job_data_complete", complete),
            "Skill and duration known" if complete else f"{job.id} is missing required_skill or duration_hours",
            action.action_id,
            refs,
        )
    )
    if not complete:
        return checks
    skill_ok = job.required_skill in worker.skills
    checks.append(
        _check(
            "skill_match",
            _verdict("skill_match", skill_ok),
            f"{worker.name} has {job.required_skill}"
            if skill_ok
            else f"{worker.name} lacks {job.required_skill} (has {', '.join(worker.skills)})",
            action.action_id,
            refs,
        )
    )
    deadline_ok = action.scheduled_date <= job.deadline
    checks.append(
        _check(
            "deadline",
            _verdict("deadline", deadline_ok),
            f"{action.scheduled_date} is by the deadline {job.deadline}"
            if deadline_ok
            else f"{action.scheduled_date} is after the deadline {job.deadline}",
            action.action_id,
            refs,
        )
    )
    start_ok = action.scheduled_date >= ctx.planning_start
    checks.append(
        _check(
            "not_before_start",
            _verdict("not_before_start", start_ok),
            "Within the planning horizon"
            if start_ok
            else f"{action.scheduled_date} is before planning start {ctx.planning_start}",
            action.action_id,
            refs,
        )
    )
    available = action.scheduled_date not in worker.unavailable_dates
    checks.append(
        _check(
            "availability",
            _verdict("availability", available),
            f"{worker.name} is available on {action.scheduled_date}"
            if available
            else f"{worker.name} is unavailable on {action.scheduled_date}",
            action.action_id,
            refs,
        )
    )
    zone_ok = worker.zone == job.zone
    checks.append(
        _check(
            "zone_match",
            _verdict("zone_match", zone_ok),
            f"Both in zone {job.zone}" if zone_ok else f"{worker.name} works in {worker.zone}, job is in {job.zone}",
            action.action_id,
            refs,
        )
    )
    return checks


def load_by_worker_day(ctx: PlanContext, actions: list[AssignJobAction]) -> dict[str, dict[str, int]]:
    load: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a in ctx.assignments:
        load[a.worker_id][a.scheduled_date.isoformat()] += a.hours
    for action in actions:
        job = ctx.jobs.get(action.job_id)
        if job is not None and job.duration_hours is not None and action.worker_id in ctx.workers:
            load[action.worker_id][action.scheduled_date.isoformat()] += job.duration_hours
    return {w: dict(days) for w, days in load.items()}


def _capacity_checks(ctx: PlanContext, actions: list[AssignJobAction]) -> list[ValidationCheck]:
    load = load_by_worker_day(ctx, actions)
    touched = {(a.worker_id, a.scheduled_date.isoformat()) for a in actions if a.worker_id in ctx.workers}
    checks = []
    for worker_id, day in sorted(touched):
        worker = ctx.workers[worker_id]
        hours = load.get(worker_id, {}).get(day, 0)
        ok = hours <= worker.capacity_hours
        action_ids = [a.action_id for a in actions if a.worker_id == worker_id and a.scheduled_date.isoformat() == day]
        for action_id in action_ids:
            checks.append(
                _check(
                    "daily_capacity",
                    _verdict("daily_capacity", ok),
                    f"{worker.name} on {day}: {hours}h of {worker.capacity_hours}h",
                    action_id,
                    [f"worker:{worker_id}"],
                )
            )
    return checks


def _plan_checks(ctx: PlanContext, actions: list[AssignJobAction]) -> list[ValidationCheck]:
    job_ids = [a.job_id for a in actions]
    duplicates = sorted({j for j in job_ids if job_ids.count(j) > 1})
    checks = [
        _check(
            "unique_job",
            _verdict("unique_job", not duplicates),
            f"Planned more than once: {', '.join(duplicates)}" if duplicates else "No job is planned twice",
            refs=[f"job:{j}" for j in duplicates],
        )
    ]
    unplanned = [j for j in ctx.requested_job_ids if j not in job_ids]
    checks.append(
        _check(
            "plan_completeness",
            _verdict("plan_completeness", not unplanned),
            f"Still unplanned: {', '.join(unplanned)}" if unplanned else "Every requested job is planned",
            refs=[f"job:{j}" for j in unplanned],
        )
    )
    return checks


def evaluate_plan(ctx: PlanContext, actions: list[AssignJobAction]) -> ValidationReport:
    checks = [c for action in actions for c in _action_checks(ctx, action)]
    checks += _capacity_checks(ctx, actions)
    checks += _plan_checks(ctx, actions)
    return ValidationReport.from_checks(checks)


@dataclass(frozen=True)
class SimulationResult:
    feasible: bool
    failed_rule_ids: list[str]
    load: dict[str, dict[str, dict[str, int]]]
    report: ValidationReport


def simulate(ctx: PlanContext, actions: list[AssignJobAction]) -> SimulationResult:
    report = evaluate_plan(ctx, actions)
    raw_load = load_by_worker_day(ctx, actions)
    load = {
        worker_id: {
            day: {"hours": hours, "capacity": ctx.workers[worker_id].capacity_hours} for day, hours in days.items()
        }
        for worker_id, days in raw_load.items()
        if worker_id in ctx.workers
    }
    return SimulationResult(
        feasible=report.ok,
        failed_rule_ids=sorted({c.rule_id for c in report.errors}),
        load=load,
        report=report,
    )

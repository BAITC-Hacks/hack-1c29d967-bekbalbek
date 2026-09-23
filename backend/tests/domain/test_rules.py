from datetime import date

import pytest

from app.domain.records import AssignmentRecord, JobRecord, PlanContext, WorkerRecord, build_plan_context
from app.domain.rules import RULES, evaluate_plan, simulate
from app.domain.schemas import AssignJobAction, CaseInput

START = date(2026, 9, 24)


def worker(**kw) -> WorkerRecord:
    base = dict(id="w-ana", name="Ana", skills=["electrical"], zone="north", capacity_hours=8, unavailable_dates=[])
    return WorkerRecord(**{**base, **kw})


def job(**kw) -> JobRecord:
    base = dict(
        id="j-101",
        title="Fix panel",
        required_skill="electrical",
        duration_hours=3,
        deadline=date(2026, 9, 25),
        priority="high",
        zone="north",
        status="unassigned",
    )
    return JobRecord(**{**base, **kw})


def ctx(workers=None, jobs=None, assignments=None, requested=None) -> PlanContext:
    workers = workers if workers is not None else [worker()]
    jobs = jobs if jobs is not None else [job()]
    return PlanContext(
        planning_start=START,
        workers={w.id: w for w in workers},
        jobs={j.id: j for j in jobs},
        assignments=list(assignments or []),
        requested_job_ids=requested or [j.id for j in jobs],
    )


def assign(job_id="j-101", worker_id="w-ana", day="2026-09-24", action_id="a1") -> AssignJobAction:
    return AssignJobAction(
        action_id=action_id, job_id=job_id, worker_id=worker_id, scheduled_date=date.fromisoformat(day)
    )


def statuses(checks, rule_id):
    return [c.status for c in checks if c.rule_id == rule_id]


def test_should_pass_every_check_for_a_valid_assignment() -> None:
    report = evaluate_plan(ctx(), [assign()])
    assert report.ok is True
    assert all(c.status == "pass" for c in report.checks)


def test_should_fail_skill_match_with_action_and_record_refs() -> None:
    report = evaluate_plan(ctx(workers=[worker(skills=["plumbing"])]), [assign()])
    failure = next(c for c in report.errors if c.rule_id == "skill_match")
    assert failure.action_id == "a1"
    assert {"job:j-101", "worker:w-ana"} <= set(failure.refs)
    assert failure.source == RULES["skill_match"].source


def test_should_fail_daily_capacity_counting_existing_assignments() -> None:
    existing = [AssignmentRecord(id="x", job_id="j-201", worker_id="w-ana", scheduled_date=START, hours=6)]
    report = evaluate_plan(ctx(assignments=existing), [assign()])
    assert "fail" in statuses(report.checks, "daily_capacity")
    assert report.ok is False


def test_should_fail_daily_capacity_across_two_proposed_actions_on_the_same_day() -> None:
    jobs = [job(), job(id="j-102", duration_hours=6)]
    report = evaluate_plan(ctx(jobs=jobs), [assign(), assign(job_id="j-102", action_id="a2")])
    assert "fail" in statuses(report.checks, "daily_capacity")


def test_should_fail_when_scheduled_after_the_deadline() -> None:
    report = evaluate_plan(ctx(), [assign(day="2026-09-26")])
    assert "fail" in statuses(report.checks, "deadline")


def test_should_fail_when_worker_is_unavailable_that_day() -> None:
    report = evaluate_plan(ctx(workers=[worker(unavailable_dates=[START])]), [assign()])
    assert "fail" in statuses(report.checks, "availability")


def test_should_warn_but_stay_ok_on_zone_mismatch() -> None:
    report = evaluate_plan(ctx(workers=[worker(zone="south")]), [assign()])
    assert statuses(report.checks, "zone_match") == ["warn"]
    assert report.ok is True


def test_should_fail_when_scheduled_before_planning_start() -> None:
    report = evaluate_plan(ctx(), [assign(day="2026-09-23")])
    assert "fail" in statuses(report.checks, "not_before_start")


def test_should_fail_record_exists_for_unknown_job_or_worker() -> None:
    report = evaluate_plan(ctx(), [assign(job_id="j-999", action_id="a1"), assign(worker_id="w-ghost", action_id="a2")])
    failures = [c for c in report.errors if c.rule_id == "record_exists"]
    assert {c.action_id for c in failures} == {"a1", "a2"}


def test_should_fail_when_job_is_already_assigned() -> None:
    report = evaluate_plan(ctx(jobs=[job(status="assigned")]), [assign()])
    assert "fail" in statuses(report.checks, "job_unassigned")


def test_should_fail_when_the_same_job_is_planned_twice() -> None:
    report = evaluate_plan(ctx(), [assign(action_id="a1"), assign(action_id="a2", day="2026-09-25")])
    assert "fail" in statuses(report.checks, "unique_job")


def test_should_fail_when_job_data_is_incomplete() -> None:
    report = evaluate_plan(ctx(jobs=[job(required_skill=None)]), [assign()])
    assert "fail" in statuses(report.checks, "job_data_complete")


def test_should_warn_when_requested_jobs_are_left_unplanned() -> None:
    jobs = [job(), job(id="j-102")]
    report = evaluate_plan(ctx(jobs=jobs), [assign()])
    completeness = next(c for c in report.checks if c.rule_id == "plan_completeness")
    assert completeness.status == "warn"
    assert "j-102" in completeness.message


def test_should_apply_job_and_capacity_overrides_when_building_context() -> None:
    case_input = CaseInput(
        planning_start=START,
        job_overrides={"j-101": {"required_skill": "hvac", "duration_hours": 5}},
        capacity_overrides={"w-ana": 4},
    )
    plan = build_plan_context(
        case_input, workers=[worker()], jobs=[job(required_skill=None, duration_hours=None)], assignments=[]
    )
    assert plan.jobs["j-101"].required_skill == "hvac"
    assert plan.jobs["j-101"].duration_hours == 5
    assert plan.workers["w-ana"].capacity_hours == 4


def test_should_restrict_requested_jobs_to_the_selected_ids() -> None:
    case_input = CaseInput(planning_start=START, job_ids=["j-102"])
    plan = build_plan_context(case_input, workers=[worker()], jobs=[job(), job(id="j-102")], assignments=[])
    assert plan.requested_job_ids == ["j-102"]


def test_should_report_load_per_worker_and_day_in_simulation() -> None:
    existing = [AssignmentRecord(id="x", job_id="j-201", worker_id="w-ana", scheduled_date=START, hours=2)]
    result = simulate(ctx(assignments=existing), [assign()])
    assert result.feasible is True
    assert result.load["w-ana"]["2026-09-24"] == {"hours": 5, "capacity": 8}


def test_should_flag_infeasible_simulation_with_the_failing_rule_ids() -> None:
    result = simulate(ctx(workers=[worker(skills=["plumbing"])]), [assign()])
    assert result.feasible is False
    assert "skill_match" in result.failed_rule_ids


@pytest.mark.parametrize(
    "rule_id", ["skill_match", "daily_capacity", "deadline", "availability", "zone_match", "not_before_start"]
)
def test_should_expose_a_source_identifier_for_every_business_rule(rule_id: str) -> None:
    assert RULES[rule_id].source

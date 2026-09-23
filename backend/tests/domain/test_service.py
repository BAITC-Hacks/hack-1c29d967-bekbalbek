from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.contracts import CaseNotFound
from app.domain.errors import ExecutionError
from app.domain.models import DispatchAssignment, DispatchJob, DispatchWorker
from app.domain.schemas import AssignJobAction, CaseInput, DispatchProposal, JobOverride
from app.domain.seed import seed
from app.domain.service import execute_actions, fingerprint, load_case_view, snapshot, validate_proposal, verify_outcome
from tests.domain.conftest import CASE, START


def case_input(**kw) -> CaseInput:
    return CaseInput(planning_start=START, **kw)


def proposal(*actions: AssignJobAction) -> DispatchProposal:
    return DispatchProposal(summary="plan", actions=list(actions))


def assign(job_id: str, worker_id: str, day: str, action_id: str = "a1") -> AssignJobAction:
    return AssignJobAction(
        action_id=action_id, job_id=job_id, worker_id=worker_id, scheduled_date=date.fromisoformat(day)
    )


async def test_should_seed_the_sample_dataset_repeatably(session_factory) -> None:
    async with session_factory() as session, session.begin():
        first = await seed(session)
    async with session_factory() as session, session.begin():
        second = await seed(session)
    assert first == second
    assert first["workers"] == 4 and first["cases"] == 3 and first["assignments"] == 2
    assert first["jobs"] >= 10


async def test_should_load_a_case_view_with_dates_records_and_rules(session_factory, seeded) -> None:
    async with session_factory() as session:
        view = await load_case_view(session, CASE)
    assert view["case_ref"] == CASE and view["planning_start"] == "2026-09-24"
    assert view["dates"][0] == "2026-09-24" and len(view["dates"]) == 7
    assert {w["id"] for w in view["workers"]} == {"w-ana", "w-boris", "w-chen", "w-dina"}
    assert all(rule["source"] for rule in view["rules"])
    assert any(j["status"] == "assigned" for j in view["jobs"]) and len(view["assignments"]) == 2


async def test_should_raise_case_not_found_for_unknown_refs(session_factory, seeded) -> None:
    async with session_factory() as session:
        with pytest.raises(CaseNotFound):
            await load_case_view(session, "nope")


async def test_should_validate_a_good_plan_against_database_records(session_factory, seeded) -> None:
    async with session_factory() as session:
        report = await validate_proposal(session, CASE, case_input(), proposal(assign("j-101", "w-chen", "2026-09-24")))
    assert report.ok is True
    assert any(c.rule_id == "plan_completeness" and c.status == "warn" for c in report.checks)


async def test_should_reject_plans_that_reference_unknown_records(session_factory, seeded) -> None:
    async with session_factory() as session:
        report = await validate_proposal(session, CASE, case_input(), proposal(assign("j-999", "w-chen", "2026-09-24")))
    assert report.ok is False and report.errors[0].rule_id == "record_exists"


async def test_should_execute_actions_and_verify_the_committed_state(session_factory, seeded) -> None:
    plan = proposal(assign("j-101", "w-chen", "2026-09-24"), assign("j-103", "w-boris", "2026-09-24", action_id="a2"))
    async with session_factory() as session, session.begin():
        results = await execute_actions(session, CASE, case_input(), plan, {"a1": "p1:a1", "a2": "p1:a2"})
    assert [r.action_id for r in results] == ["a1", "a2"]
    assert "Chen" in results[0].summary and "2026-09-24" in results[0].summary

    async with session_factory() as session:
        report = await verify_outcome(session, CASE, case_input(), plan, results)
        job = await session.get(DispatchJob, "j-101")
        assignment = (
            await session.execute(select(DispatchAssignment).where(DispatchAssignment.job_id == "j-101"))
        ).scalar_one()
    assert report.ok is True and len(report.checks) >= 3
    assert job.status == "assigned" and assignment.source_action_key == "p1:a1" and assignment.hours == 3


async def test_should_refuse_to_execute_when_the_job_is_no_longer_unassigned(session_factory, seeded) -> None:
    plan = proposal(assign("j-201", "w-ana", "2026-09-24"))
    async with session_factory() as session, session.begin():
        with pytest.raises(ExecutionError) as exc:
            await execute_actions(session, CASE, case_input(), plan, {"a1": "p1:a1"})
    assert exc.value.code == "job_not_unassigned"


async def test_should_enforce_unique_action_keys_in_the_database(session_factory, seeded) -> None:
    plan = proposal(assign("j-101", "w-chen", "2026-09-24"))
    async with session_factory() as session, session.begin():
        await execute_actions(session, CASE, case_input(), plan, {"a1": "p1:a1"})
    async with session_factory() as session:
        session.add(
            DispatchAssignment(
                job_id="j-102", worker_id="w-ana", scheduled_date=START, hours=1, source_action_key="p1:a1"
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_should_persist_job_overrides_when_executing(session_factory, seeded) -> None:
    ci = case_input(job_overrides={"j-107": JobOverride(required_skill="electrical", duration_hours=2)})
    plan = proposal(assign("j-107", "w-ana", "2026-09-24"))
    async with session_factory() as session, session.begin():
        await execute_actions(session, "case-dispatch-002", ci, plan, {"a1": "p2:a1"})
    async with session_factory() as session:
        job = await session.get(DispatchJob, "j-107")
    assert job.required_skill == "electrical" and job.duration_hours == 2 and job.status == "assigned"


async def test_should_fail_verification_when_the_expected_assignment_is_missing(session_factory, seeded) -> None:
    plan = proposal(assign("j-101", "w-chen", "2026-09-24"))
    async with session_factory() as session:
        report = await verify_outcome(session, CASE, case_input(), plan, [])
    assert report.ok is False


async def test_should_change_the_fingerprint_only_when_relevant_data_changes(session_factory, seeded) -> None:
    plan = proposal(assign("j-101", "w-chen", "2026-09-24"))
    async with session_factory() as session:
        before = await fingerprint(session, CASE, case_input(), plan)
        again = await fingerprint(session, CASE, case_input(), plan)
    assert before == again and len(before) == 64
    async with session_factory() as session, session.begin():
        worker = await session.get(DispatchWorker, "w-chen")
        worker.unavailable_dates = [*worker.unavailable_dates, "2026-09-24"]
    async with session_factory() as session:
        after = await fingerprint(session, CASE, case_input(), plan)
    assert after != before


async def test_should_snapshot_worker_load_by_date(session_factory, seeded) -> None:
    async with session_factory() as session:
        snap = await snapshot(session, CASE, case_input())
    ana = next(w for w in snap["workers"] if w["id"] == "w-ana")
    assert ana["load_by_date"]["2026-09-24"] == 4 and ana["capacity_hours"] == 8
    assert {a["job_id"] for a in snap["assignments"]} == {"j-201", "j-202"}


async def test_should_expose_the_source_action_key_of_applied_assignments_in_the_case_view(
    session_factory, seeded
) -> None:
    plan = proposal(assign("j-101", "w-chen", "2026-09-24"))
    async with session_factory() as session, session.begin():
        await execute_actions(session, CASE, case_input(), plan, {"a1": "p1:a1"})

    async with session_factory() as session:
        view = await load_case_view(session, CASE)
    by_job = {a["job_id"]: a for a in view["assignments"]}
    assert by_job["j-101"]["source_action_key"] == "p1:a1"
    assert by_job["j-201"]["source_action_key"] is None  # seeded row, not created by an agent

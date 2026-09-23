import dataclasses

import pytest
from agents.testing import assistant_message
from sqlalchemy import func, select

from app.core.apply_service import ApplyError, ApplyService
from app.core.contracts import ExecutionError, VerificationCheck, VerificationReport
from app.core.run_service import RunService
from app.db.models import Application
from app.domain.models import DispatchAssignment, DispatchJob, DispatchWorker
from tests.core.scripted import SMALL_PLAN, happy_script, needs_input_output, scripted, tool

CASE = "case-dispatch-001"


async def proposed_run(session_factory, domain, settings, bus, actions=SMALL_PLAN):
    service = RunService(session_factory, domain, settings, bus, model_factory=lambda _run: happy_script(actions))
    run = await service.create_run(case_ref=CASE, goal="g", input={"planning_start": "2026-09-24"})
    await service.execute(run.id)
    detail = await service.get_run_detail(run.id)
    assert detail.run.status == "proposed"
    return service, detail


async def assignment_count(session_factory) -> int:
    async with session_factory() as session:
        return (await session.execute(select(func.count()).select_from(DispatchAssignment))).scalar_one()


async def test_should_apply_once_verify_and_record_every_action(session_factory, domain, settings, bus, seeded) -> None:
    service, detail = await proposed_run(session_factory, domain, settings, bus)
    apply = ApplyService(session_factory, domain, bus)

    application = await apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version)

    assert application.status == "verified" and application.verification["ok"] is True
    assert [a.action_id for a in application.actions] == ["a1", "a3"] and all(
        a.status == "applied" for a in application.actions
    )
    assert "Chen" in application.actions[0].summary
    after = await service.get_run_detail(detail.run.id)
    assert after.run.status == "verified" and after.proposal.status == "applied" and after.snapshot_after is not None
    assert after.snapshot_after["workers"][2]["load_by_date"]["2026-09-24"] == 3
    assert await assignment_count(session_factory) == 4
    async with session_factory() as session:
        assert (await session.get(DispatchJob, "j-101")).status == "assigned"
    types = [e.type for e in await bus.replay(detail.run.id)]
    assert types[-4:] == ["action_applied", "action_applied", "verification_finished", "run_finished"]
    assert (await bus.replay(detail.run.id))[-1].run_status == "verified"


async def test_should_reject_a_duplicate_apply_without_writing_twice(
    session_factory, domain, settings, bus, seeded
) -> None:
    _, detail = await proposed_run(session_factory, domain, settings, bus)
    apply = ApplyService(session_factory, domain, bus)
    await apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version)

    with pytest.raises(ApplyError) as exc:
        await apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version)
    assert exc.value.code == "duplicate_apply"
    assert await assignment_count(session_factory) == 4


async def test_should_reject_concurrent_duplicate_applies(session_factory, domain, settings, bus, seeded) -> None:
    import asyncio

    _, detail = await proposed_run(session_factory, domain, settings, bus)
    apply = ApplyService(session_factory, domain, bus)
    results = await asyncio.gather(
        apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version),
        apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version),
        return_exceptions=True,
    )
    errors = [r for r in results if isinstance(r, ApplyError)]
    successes = [r for r in results if not isinstance(r, BaseException)]
    assert len(successes) == 1 and len(errors) == 1 and errors[0].code == "duplicate_apply"
    assert await assignment_count(session_factory) == 4


async def test_should_reject_a_stale_proposal_when_the_data_changed(
    session_factory, domain, settings, bus, seeded
) -> None:
    service, detail = await proposed_run(session_factory, domain, settings, bus)
    async with session_factory() as session, session.begin():
        chen = await session.get(DispatchWorker, "w-chen")
        chen.unavailable_dates = [*chen.unavailable_dates, "2026-09-24"]

    with pytest.raises(ApplyError) as exc:
        await ApplyService(session_factory, domain, bus).apply(
            detail.run.id, detail.proposal.id, detail.proposal.version
        )

    assert exc.value.code == "stale_proposal"
    assert exc.value.details["fingerprint_changed"] is True
    assert any(c["rule_id"] == "availability" for c in exc.value.details["validation"]["errors"])
    after = await service.get_run_detail(detail.run.id)
    assert (
        after.run.status == "proposed" and after.proposal.status == "stale" and after.application.status == "rejected"
    )
    assert await assignment_count(session_factory) == 2
    assert [e.type for e in await bus.replay(detail.run.id)][-2:] == ["apply_started", "apply_rejected"]


async def test_should_reject_wrong_proposal_versions_and_ids(session_factory, domain, settings, bus, seeded) -> None:
    _, detail = await proposed_run(session_factory, domain, settings, bus)
    apply = ApplyService(session_factory, domain, bus)
    with pytest.raises(ApplyError) as exc:
        await apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version + 1)
    assert exc.value.code == "invalid_state"
    with pytest.raises(ApplyError):
        await apply.apply(detail.run.id, detail.run.id, detail.proposal.version)


async def test_should_reject_runs_that_are_not_in_proposed_state(
    session_factory, domain, settings, bus, seeded
) -> None:
    service = RunService(
        session_factory,
        domain,
        settings,
        bus,
        model_factory=lambda _run: scripted([tool("get_case")], [assistant_message(needs_input_output())]),
    )
    run = await service.create_run(case_ref="case-dispatch-002", goal="g", input={"planning_start": "2026-09-24"})
    await service.execute(run.id)
    with pytest.raises(ApplyError) as exc:
        await ApplyService(session_factory, domain, bus).apply(run.id, run.id, 1)
    assert exc.value.code == "invalid_state"


async def test_should_roll_back_every_write_when_execution_fails_midway(
    session_factory, domain, settings, bus, seeded
) -> None:
    service, detail = await proposed_run(session_factory, domain, settings, bus)
    original = domain.execute_actions

    async def flaky(session, case_ref, case_input, proposal, action_keys):
        await original(session, case_ref, case_input, proposal, action_keys)
        raise ExecutionError("simulated_failure", "second write failed")

    apply = ApplyService(session_factory, dataclasses.replace(domain, execute_actions=flaky), bus)
    with pytest.raises(ApplyError) as exc:
        await apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version)

    assert exc.value.code == "execution_failed"
    assert await assignment_count(session_factory) == 2
    after = await service.get_run_detail(detail.run.id)
    assert after.run.status == "failed" and after.run.error["stage"] == "apply" and after.application.status == "failed"
    async with session_factory() as session:
        assert (await session.get(DispatchJob, "j-101")).status == "unassigned"
    assert (await bus.replay(detail.run.id))[-1].type == "run_failed"


async def test_should_mark_the_run_failed_when_verification_fails(
    session_factory, domain, settings, bus, seeded
) -> None:
    service, detail = await proposed_run(session_factory, domain, settings, bus)

    async def pessimistic(session, case_ref, case_input, proposal, results):
        return VerificationReport.from_checks(
            [VerificationCheck(id="x", label="x", ok=False, detail="nope")], "not confirmed"
        )

    apply = ApplyService(session_factory, dataclasses.replace(domain, verify_outcome=pessimistic), bus)
    application = await apply.apply(detail.run.id, detail.proposal.id, detail.proposal.version)
    assert application.status == "failed" and application.verification["ok"] is False
    after = await service.get_run_detail(detail.run.id)
    assert after.run.status == "failed" and after.run.error["stage"] == "verification"
    events = await bus.replay(detail.run.id)
    assert [e.type for e in events][-2:] == ["verification_finished", "run_failed"]
    async with session_factory() as session:
        assert (await session.execute(select(func.count()).select_from(Application))).scalar_one() == 1

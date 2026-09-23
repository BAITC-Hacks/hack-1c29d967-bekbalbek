import asyncio
import dataclasses
import uuid

import pytest
from agents import RunContextWrapper
from agents.testing import ModelStep, assistant_message
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import Settings
from app.core.context import RunContext
from app.core.contracts import CaseNotFound, ToolSpec
from app.core.run_service import RunService, mark_interrupted_runs
from app.db.models import Proposal, Run, RunMessage
from tests.core.scripted import (
    BAD_PLAN,
    FULL_PLAN,
    happy_script,
    infeasible_output,
    needs_input_output,
    proposal_output,
    scripted,
    tool,
)

CASE = "case-dispatch-001"
GOAL = "Assign every open job."


def make_service(session_factory, domain, settings, bus, model) -> RunService:
    return RunService(session_factory, domain, settings, bus, model_factory=lambda _run: model)


async def run_to_completion(service: RunService, case_ref: str = CASE, input: dict | None = None, **options):
    run = await service.create_run(
        case_ref=case_ref, goal=GOAL, input=input or {"planning_start": "2026-09-24"}, **options
    )
    await service.execute(run.id)
    return run.id


async def test_should_create_a_queued_run_with_validated_input(session_factory, domain, settings, bus, seeded) -> None:
    service = make_service(session_factory, domain, settings, bus, happy_script())
    run = await service.create_run(
        case_ref=CASE, goal=GOAL, input={"planning_start": "2026-09-24", "job_ids": ["j-101"]}
    )
    assert run.status == "queued" and run.input == {
        "planning_start": "2026-09-24",
        "job_ids": ["j-101"],
        "job_overrides": {},
        "capacity_overrides": {},
        "notes": None,
    }
    assert run.model == "scripted" and run.max_turns == 8


async def test_should_reject_invalid_input_and_unknown_cases(session_factory, domain, settings, bus, seeded) -> None:
    service = make_service(session_factory, domain, settings, bus, happy_script())
    with pytest.raises(ValidationError):
        await service.create_run(case_ref=CASE, goal=GOAL, input={"planning_start": "not-a-date"})
    with pytest.raises(CaseNotFound):
        await service.create_run(case_ref="nope", goal=GOAL, input={"planning_start": "2026-09-24"})


async def test_should_produce_a_validated_proposal_from_real_tool_calls(
    session_factory, domain, settings, bus, seeded
) -> None:
    service = make_service(session_factory, domain, settings, bus, happy_script())
    run_id = await run_to_completion(service)

    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "proposed" and detail.run.outcome == "proposal_ready"
    assert detail.proposal is not None and detail.proposal.version == 1 and detail.proposal.status == "validated"
    assert detail.proposal.validation["ok"] is True and len(detail.proposal.content["actions"]) == 6
    assert len(detail.proposal.basis_fingerprint) == 64
    assert detail.snapshot_before is not None and detail.run.stats.tool_calls == 4
    assert detail.run.stats.usage is not None and detail.run.stats.duration_ms is not None

    types = [e.type for e in await bus.replay(run_id)]
    assert types == [
        "run_started",
        *(["tool_started", "tool_finished"] * 4),
        "agent_output",
        "proposal_ready",
        "run_finished",
    ]
    finished = (await bus.replay(run_id))[-1]
    assert (
        finished.run_status == "proposed"
        and finished.payload["outcome"] == "proposal_ready"
        and finished.payload["tool_calls"] == 4
    )


async def test_should_persist_the_conversation_history(session_factory, domain, settings, bus, seeded) -> None:
    service = make_service(session_factory, domain, settings, bus, happy_script())
    run_id = await run_to_completion(service)
    async with session_factory() as session:
        rows = (
            (await session.execute(select(RunMessage).where(RunMessage.run_id == run_id).order_by(RunMessage.seq)))
            .scalars()
            .all()
        )
    kinds = [r.kind for r in rows]
    assert kinds[0] == "message" and rows[0].role == "user"
    assert kinds.count("tool_call") == 4 and kinds.count("tool_output") == 4 and kinds[-1] == "final_output"


async def test_should_end_with_needs_input_and_the_missing_fields(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted([tool("get_case")], [assistant_message(needs_input_output())])
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service, case_ref="case-dispatch-002")

    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "needs_input" and detail.proposal is None
    assert detail.needs_input["missing_fields"][0]["field"] == "jobs.j-107.required_skill"
    assert [e.type for e in await bus.replay(run_id)][-2:] == ["agent_output", "run_finished"]


async def test_should_end_with_infeasible_and_blocking_constraints(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted([tool("get_case")], [assistant_message(infeasible_output())])
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service, case_ref="case-dispatch-003")

    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "infeasible"
    assert {c["rule_id"] for c in detail.infeasible["blocking_constraints"]} == {"skill_match", "daily_capacity"}


async def test_should_reject_a_bad_proposal_then_accept_the_revision(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted(
        [tool("get_case")],
        [assistant_message(proposal_output(BAD_PLAN))],
        [assistant_message(proposal_output(FULL_PLAN))],
    )
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service)

    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "proposed"
    assert [(p.version, p.status) for p in detail.proposals] == [(1, "rejected"), (2, "validated")]
    assert detail.proposal.version == 2

    events = await bus.replay(run_id)
    types = [e.type for e in events]
    assert types[-5:] == ["validation_failed", "revision_started", "agent_output", "proposal_ready", "run_finished"]
    failed = next(e for e in events if e.type == "validation_failed")
    assert failed.payload["will_revise"] is True and failed.payload["errors"][0]["rule_id"] == "skill_match"
    revision_input = model.calls[-1].input
    assert any("skill_match" in str(item) for item in revision_input)


async def test_should_stop_after_the_bounded_number_of_revisions(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted([assistant_message(proposal_output(BAD_PLAN))], [assistant_message(proposal_output(BAD_PLAN))])
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service)

    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "validation_failed" and detail.run.error is None
    assert [p.status for p in detail.proposals] == ["rejected", "rejected"]
    failures = [e for e in await bus.replay(run_id) if e.type == "validation_failed"]
    assert [f.payload["will_revise"] for f in failures] == [True, False]
    assert (await bus.replay(run_id))[-1].run_status == "validation_failed"


async def test_should_fail_cleanly_when_the_turn_limit_is_exceeded(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted(*[[tool("lookup_rules", {}, f"c{i}")] for i in range(6)])
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service, max_turns=2)

    detail = await service.get_run_detail(run_id)
    assert (
        detail.run.status == "failed" and detail.run.error["code"] == "max_turns_exceeded" and detail.run.max_turns == 2
    )
    assert (await bus.replay(run_id))[-1].type == "run_failed"


async def test_should_record_tool_failures_and_let_the_agent_continue(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted(
        [tool("find_resources", {"skill": None, "on_date": "not-a-date"})],
        [assistant_message(proposal_output(FULL_PLAN))],
    )
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service)

    events = await bus.replay(run_id)
    failed = next(e for e in events if e.type == "tool_failed")
    assert (
        failed.payload["error"]["code"] == "invalid_arguments"
        and failed.payload["label"] == "Checking available workers"
    )
    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "proposed" and detail.run.stats.tool_calls == 1


async def test_should_fail_with_timeout_when_the_run_takes_too_long(session_factory, domain, bus, seeded) -> None:
    async def slow(ctx: RunContextWrapper[RunContext]) -> dict:
        """Slow tool."""
        await asyncio.sleep(2)
        return {}

    slow_domain = dataclasses.replace(domain, tools=[ToolSpec(name="get_case", label="Slow", fn=slow)])
    settings = Settings(agent_run_timeout_seconds=0.2, tool_timeout_seconds=5, openai_model="scripted")
    service = make_service(
        session_factory,
        slow_domain,
        settings,
        bus,
        scripted([tool("get_case")], [assistant_message(proposal_output(FULL_PLAN))]),
    )
    run_id = await run_to_completion(service)

    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "failed" and detail.run.error["code"] == "timeout"


async def test_should_fail_when_the_model_raises(session_factory, domain, settings, bus, seeded) -> None:
    model = scripted(ModelStep.raise_error(RuntimeError("provider down")))
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service)

    detail = await service.get_run_detail(run_id)
    assert (
        detail.run.status == "failed"
        and detail.run.error["code"] == "agent_error"
        and "RuntimeError" in detail.run.error["message"]
    )
    last = (await bus.replay(run_id))[-1]
    assert last.type == "run_failed" and last.payload["stage"] == "analysis"


async def test_should_fail_when_proposal_ready_comes_without_a_proposal(
    session_factory, domain, settings, bus, seeded
) -> None:
    model = scripted(
        [
            assistant_message(
                '{"outcome": "proposal_ready", "message": "done", "proposal": null, "missing_fields": [], "blocking_constraints": []}'
            )
        ]
    )
    service = make_service(session_factory, domain, settings, bus, model)
    run_id = await run_to_completion(service)
    detail = await service.get_run_detail(run_id)
    assert detail.run.status == "failed" and detail.run.error["code"] == "invalid_output"


async def test_should_mark_in_flight_runs_as_interrupted_on_startup(session_factory, bus, seeded) -> None:
    async with session_factory() as session, session.begin():
        ids = []
        for status in ("queued", "analyzing", "applying", "proposed", "verified"):
            run = Run(case_ref=CASE, goal=GOAL, input={}, status=status, model="scripted", max_turns=3)
            session.add(run)
            await session.flush()
            ids.append((run.id, status))

    interrupted = await mark_interrupted_runs(session_factory, bus)
    assert interrupted == 3
    async with session_factory() as session:
        statuses = {rid: (await session.get(Run, rid)).status for rid, _ in ids}
    assert [statuses[rid] for rid, _ in ids] == ["interrupted", "interrupted", "interrupted", "proposed", "verified"]
    events = await bus.replay(ids[1][0])
    assert events[-1].type == "run_failed" and events[-1].payload["code"] == "interrupted"


async def test_should_list_runs_newest_first(session_factory, domain, settings, bus, seeded) -> None:
    service = make_service(session_factory, domain, settings, bus, happy_script())
    first = await service.create_run(case_ref=CASE, goal=GOAL, input={"planning_start": "2026-09-24"})
    second = await service.create_run(case_ref=CASE, goal="second", input={"planning_start": "2026-09-24"})
    runs = await service.list_runs(limit=10)
    assert [r.id for r in runs] == [second.id, first.id]
    assert await service.get_run_detail(uuid.uuid4()) is None
    async with session_factory() as session:
        assert (await session.execute(select(func.count()).select_from(Proposal))).scalar_one() == 0

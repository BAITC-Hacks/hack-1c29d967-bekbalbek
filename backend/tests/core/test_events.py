import asyncio
import uuid

from app.core.events import EventBus
from app.db.models import Run


async def make_run(session_factory, status: str = "analyzing") -> uuid.UUID:
    async with session_factory() as session, session.begin():
        run = Run(case_ref="case-1", goal="g", input={}, status=status, model="scripted", max_turns=5)
        session.add(run)
        await session.flush()
        return run.id


async def test_should_persist_events_with_a_per_run_sequence(session_factory) -> None:
    bus = EventBus(session_factory)
    run_a, run_b = await make_run(session_factory), await make_run(session_factory)

    first = await bus.emit(run_a, "run_started", {"goal": "g"}, run_status="analyzing")
    second = await bus.emit(run_a, "tool_started", {"tool": "get_meeting"}, run_status="analyzing")
    other = await bus.emit(run_b, "run_started", {}, run_status="analyzing")

    assert (first.id, second.id, other.id) == (1, 2, 1)
    assert first.type == "run_started" and first.run_status == "analyzing" and first.payload == {"goal": "g"}
    assert first.ts.tzinfo is not None


async def test_should_replay_events_after_a_sequence_number(session_factory) -> None:
    bus = EventBus(session_factory)
    run_id = await make_run(session_factory)
    for i in range(4):
        await bus.emit(run_id, "tool_started", {"i": i}, run_status="analyzing")

    replayed = await bus.replay(run_id, after_seq=2)
    assert [e.id for e in replayed] == [3, 4]
    assert [e.id for e in await bus.replay(run_id)] == [1, 2, 3, 4]


async def test_should_deliver_live_events_only_to_subscribers_of_that_run(session_factory) -> None:
    bus = EventBus(session_factory)
    run_a, run_b = await make_run(session_factory), await make_run(session_factory)

    async with bus.subscribe(run_a) as queue:
        await bus.emit(run_b, "run_started", {}, run_status="analyzing")
        emitted = await bus.emit(run_a, "run_started", {"x": 1}, run_status="analyzing")
        received = await asyncio.wait_for(queue.get(), timeout=1)

    assert received.id == emitted.id and received.payload == {"x": 1}
    assert queue.empty()


async def test_should_stream_replayed_then_live_events_without_duplicates_until_terminal(session_factory) -> None:
    bus = EventBus(session_factory)
    run_id = await make_run(session_factory)
    await bus.emit(run_id, "run_started", {}, run_status="analyzing")
    await bus.emit(run_id, "tool_started", {}, run_status="analyzing")

    async def produce() -> None:
        await asyncio.sleep(0.05)
        await bus.emit(run_id, "tool_finished", {}, run_status="analyzing")
        await bus.emit(run_id, "run_finished", {}, run_status="verified")
        await bus.emit(run_id, "ignored", {}, run_status="verified")

    producer = asyncio.create_task(produce())
    seen = [e async for e in bus.stream(run_id, after_seq=1)]
    await producer

    assert [(e.id, e.type) for e in seen] == [(2, "tool_started"), (3, "tool_finished"), (4, "run_finished")]


async def test_should_end_the_stream_immediately_when_the_run_is_already_terminal(session_factory) -> None:
    bus = EventBus(session_factory)
    run_id = await make_run(session_factory, status="failed")
    await bus.emit(run_id, "run_failed", {"code": "x"}, run_status="failed")

    seen = await asyncio.wait_for(_collect(bus.stream(run_id)), timeout=1)
    assert [e.type for e in seen] == ["run_failed"]


async def _collect(agen):
    return [e async for e in agen]

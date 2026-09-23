import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.serialization import jsonable
from app.core.status import is_terminal
from app.db.models import Run, RunEvent

TERMINAL_EVENT_TYPES = frozenset({"run_finished", "run_failed"})
MAX_SUBSCRIBERS_PER_RUN = 32


class TooManySubscribers(Exception):
    pass


class RunEventDTO(BaseModel):
    id: int
    run_id: UUID
    type: str
    ts: datetime
    run_status: str
    payload: dict[str, Any]


def _to_dto(row: RunEvent) -> RunEventDTO:
    return RunEventDTO(
        id=row.seq, run_id=row.run_id, type=row.type, ts=row.created_at, run_status=row.run_status, payload=row.payload
    )


def ends_stream(event: RunEventDTO) -> bool:
    return event.type in TERMINAL_EVENT_TYPES and is_terminal(event.run_status)


class EventBus:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._subscribers: dict[UUID, set[asyncio.Queue[RunEventDTO]]] = defaultdict(set)
        self._locks: dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def emit(self, run_id: UUID, event_type: str, payload: dict[str, Any], *, run_status: str) -> RunEventDTO:
        async with self._locks[run_id]:
            dto = await self._persist(run_id, event_type, jsonable(payload), run_status)
        for queue in list(self._subscribers.get(run_id, ())):
            queue.put_nowait(dto)
        return dto

    async def _persist(self, run_id: UUID, event_type: str, payload: dict[str, Any], run_status: str) -> RunEventDTO:
        last_error: IntegrityError | None = None
        for _ in range(5):
            try:
                async with self._session_factory() as session, session.begin():
                    current = await session.execute(
                        select(func.coalesce(func.max(RunEvent.seq), 0)).where(RunEvent.run_id == run_id)
                    )
                    row = RunEvent(
                        run_id=run_id,
                        seq=current.scalar_one() + 1,
                        type=event_type,
                        run_status=run_status,
                        payload=payload,
                        created_at=datetime.now(UTC),
                    )
                    session.add(row)
                    await session.flush()
                    return _to_dto(row)
            except IntegrityError as exc:
                last_error = exc
        raise RuntimeError(f"could not allocate event sequence for run {run_id}") from last_error

    async def replay(self, run_id: UUID, after_seq: int = 0) -> list[RunEventDTO]:
        async with self._session_factory() as session:
            rows = await session.execute(
                select(RunEvent).where(RunEvent.run_id == run_id, RunEvent.seq > after_seq).order_by(RunEvent.seq)
            )
            return [_to_dto(row) for row in rows.scalars()]

    @asynccontextmanager
    async def subscribe(self, run_id: UUID) -> AsyncIterator[asyncio.Queue[RunEventDTO]]:
        if self.subscriber_count(run_id) >= MAX_SUBSCRIBERS_PER_RUN:
            raise TooManySubscribers(f"run {run_id} already has {MAX_SUBSCRIBERS_PER_RUN} event streams")
        queue: asyncio.Queue[RunEventDTO] = asyncio.Queue()
        self._subscribers[run_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[run_id].discard(queue)
            if not self._subscribers[run_id]:
                self._subscribers.pop(run_id, None)

    def subscriber_count(self, run_id: UUID) -> int:
        return len(self._subscribers.get(run_id, ()))

    async def _run_status(self, run_id: UUID) -> str | None:
        async with self._session_factory() as session:
            return (await session.execute(select(Run.status).where(Run.id == run_id))).scalar_one_or_none()

    async def stream(self, run_id: UUID, after_seq: int = 0) -> AsyncIterator[RunEventDTO]:
        async with self.subscribe(run_id) as queue:
            last_seq = after_seq
            for event in await self.replay(run_id, after_seq):
                last_seq = event.id
                yield event
                if ends_stream(event):
                    return
            status = await self._run_status(run_id)
            if status is None or is_terminal(status):
                return
            while True:
                event = await queue.get()
                if event.id <= last_seq:
                    continue
                last_seq = event.id
                yield event
                if ends_stream(event):
                    return

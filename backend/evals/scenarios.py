from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import repo
from app.domain.models import ActionItem, Protocol
from app.speech.align import SpokenSegment


async def prepare_transcript(session: AsyncSession) -> None:
    await session.execute(delete(Protocol).where(Protocol.meeting_id == "m-sample-1"))
    await repo.replace_transcript(
        session, "m-sample-1", [SpokenSegment(0, 4, "S1", "ru", "Гульмира, подготовьте отчёт до пятницы.", [])], 4
    )
    await repo.set_status(session, "m-sample-1", "ready")


async def final_state_ok(session: AsyncSession, case_ref: str) -> bool:
    return (
        await session.scalar(select(func.count()).select_from(ActionItem).where(ActionItem.meeting_id == case_ref)) == 1
    )


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
    final_state_ok: Callable[[AsyncSession, str], Awaitable[bool]] = final_state_ok
    goal: str = "Составь протокол совещания"
    options: dict[str, Any] = field(default_factory=dict)


SCENARIOS = [
    Scenario(
        "protocol_evidence",
        "Стенограмма → поручение с цитатой → подтверждение → проверка БД",
        "m-sample-1",
        {"meeting_date": "2026-09-23"},
        "auto",
        "verified",
        "proposal_ready",
        apply=True,
    )
]

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Application, Proposal, Run, RunMessage


class RunStatsDTO(BaseModel):
    duration_ms: int | None
    tool_calls: int
    usage: dict[str, Any] | None


class RunDTO(BaseModel):
    id: UUID
    case_ref: str
    goal: str
    input: dict[str, Any]
    status: str
    outcome: str | None
    model: str
    max_turns: int
    error: dict[str, Any] | None
    stats: RunStatsDTO
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime


class ProposalDTO(BaseModel):
    id: UUID
    run_id: UUID
    version: int
    status: str
    content: dict[str, Any]
    validation: dict[str, Any]
    basis_fingerprint: str
    created_at: datetime


class ActionDTO(BaseModel):
    id: UUID
    action_id: str
    type: str
    status: str
    result: dict[str, Any] | None
    summary: str


class ApplicationDTO(BaseModel):
    id: UUID
    proposal_id: UUID
    version: int
    status: str
    actions: list[ActionDTO]
    verification: dict[str, Any] | None
    error: dict[str, Any] | None
    started_at: datetime
    finished_at: datetime | None


class RunMessageDTO(BaseModel):
    seq: int
    role: str
    kind: str
    content: Any
    created_at: datetime


class RunDetailDTO(BaseModel):
    run: RunDTO
    proposals: list[ProposalDTO]
    proposal: ProposalDTO | None
    needs_input: dict[str, Any] | None
    infeasible: dict[str, Any] | None
    application: ApplicationDTO | None
    snapshot_before: dict[str, Any] | None
    snapshot_after: dict[str, Any] | None
    messages: list[RunMessageDTO]


def run_to_dto(run: Run) -> RunDTO:
    return RunDTO(
        id=run.id,
        case_ref=run.case_ref,
        goal=run.goal,
        input=run.input,
        status=run.status,
        outcome=run.outcome,
        model=run.model,
        max_turns=run.max_turns,
        error=run.error,
        stats=RunStatsDTO(duration_ms=run.duration_ms, tool_calls=run.tool_call_count, usage=run.usage),
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        updated_at=run.updated_at,
    )


def proposal_to_dto(proposal: Proposal) -> ProposalDTO:
    return ProposalDTO(
        id=proposal.id,
        run_id=proposal.run_id,
        version=proposal.version,
        status=proposal.status,
        content=proposal.content,
        validation=proposal.validation,
        basis_fingerprint=proposal.basis_fingerprint,
        created_at=proposal.created_at,
    )


def application_to_dto(application: Application) -> ApplicationDTO:
    return ApplicationDTO(
        id=application.id,
        proposal_id=application.proposal_id,
        version=application.version,
        status=application.status,
        actions=[
            ActionDTO(id=a.id, action_id=a.action_id, type=a.type, status=a.status, result=a.result, summary=a.summary)
            for a in application.actions
        ],
        verification=application.verification,
        error=application.error,
        started_at=application.started_at,
        finished_at=application.finished_at,
    )


def _outcome_section(run: Run, outcome: str, key: str) -> dict[str, Any] | None:
    if run.outcome != outcome or not run.agent_result:
        return None
    return {"message": run.agent_result.get("message", ""), key: run.agent_result.get(key, [])}


async def load_application(session: AsyncSession, application_id: UUID) -> Application | None:
    result = await session.execute(
        select(Application).where(Application.id == application_id).options(selectinload(Application.actions))
    )
    return result.scalar_one_or_none()


async def load_run_detail(session: AsyncSession, run_id: UUID) -> RunDetailDTO | None:
    run = await session.get(Run, run_id)
    if run is None:
        return None
    proposals = (
        (await session.execute(select(Proposal).where(Proposal.run_id == run_id).order_by(Proposal.version)))
        .scalars()
        .all()
    )
    application = (
        await session.execute(
            select(Application)
            .where(Application.run_id == run_id)
            .options(selectinload(Application.actions))
            .order_by(Application.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    messages = (
        (await session.execute(select(RunMessage).where(RunMessage.run_id == run_id).order_by(RunMessage.seq)))
        .scalars()
        .all()
    )
    proposal_dtos = [proposal_to_dto(p) for p in proposals]
    return RunDetailDTO(
        run=run_to_dto(run),
        proposals=proposal_dtos,
        proposal=proposal_dtos[-1] if proposal_dtos else None,
        needs_input=_outcome_section(run, "needs_input", "missing_fields"),
        infeasible=_outcome_section(run, "infeasible", "blocking_constraints"),
        application=application_to_dto(application) if application else None,
        snapshot_before=run.snapshot_before,
        snapshot_after=run.snapshot_after,
        messages=[
            RunMessageDTO(seq=m.seq, role=m.role, kind=m.kind, content=m.content, created_at=m.created_at)
            for m in messages
        ],
    )

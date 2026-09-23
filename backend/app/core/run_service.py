import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from agents import AgentsException, MaxTurnsExceeded, Model, RunResult
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.agent_runtime import AgentRuntime
from app.core.context import RunContext
from app.core.contracts import AgentOutputBase, DomainModule, ProposalBase, ValidationReport, structural_checks
from app.core.errors import InvalidOutputError
from app.core.events import EventBus
from app.core.read_models import RunDetailDTO, RunDTO, load_run_detail, run_to_dto
from app.core.serialization import jsonable
from app.core.status import IN_FLIGHT_STATUSES
from app.db.models import Proposal, Run, RunMessage

logger = logging.getLogger(__name__)


@dataclass
class _RunState:
    status: str
    started: float = field(default_factory=time.perf_counter)
    usage: dict[str, int] = field(
        default_factory=lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    )
    revisions: int = 0

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)

    def add_usage(self, usage: Any) -> None:
        for key in self.usage:
            self.usage[key] += int(getattr(usage, key, 0) or 0)


def _message_kind(item: dict[str, Any]) -> tuple[str, str]:
    kinds = {"function_call": ("tool_call", "assistant"), "function_call_output": ("tool_output", "tool")}
    if item.get("type") in kinds:
        return kinds[item["type"]]
    if item.get("type", "message") == "message":
        return "message", str(item.get("role", "assistant"))
    return "other", "assistant"


def revision_prompt(report: ValidationReport) -> str:
    lines = [
        f"- [{c.rule_id}] {c.message}" + (f" (action {c.action_id})" if c.action_id else "") for c in report.errors
    ]
    return (
        "The proposal was rejected by the business-rule validator. Fix every failing check below, re-run simulate_plan, "
        "and return a corrected proposal (or needs_input / infeasible if it truly cannot be fixed):\n"
        + "\n".join(lines)
    )


class RunService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        domain: DomainModule,
        settings: Settings,
        bus: EventBus,
        model_factory: Callable[[RunDTO], str | Model],
    ) -> None:
        self._sf = session_factory
        self._domain = domain
        self._settings = settings
        self._bus = bus
        self._model_factory = model_factory

    async def create_run(
        self, *, case_ref: str, goal: str, input: dict[str, Any], max_turns: int | None = None
    ) -> RunDTO:
        case_input = self._domain.case_input_model.model_validate(input)
        async with self._sf() as session:
            await self._domain.load_case_view(session, case_ref)
        run = Run(
            case_ref=case_ref,
            goal=goal,
            input=case_input.model_dump(mode="json"),
            status="queued",
            model=str(self._settings.openai_model),
            max_turns=max_turns or self._settings.agent_max_turns,
        )
        async with self._sf() as session, session.begin():
            session.add(run)
            await session.flush()
            await session.refresh(run)
        return run_to_dto(run)

    async def list_runs(self, limit: int = 50) -> list[RunDTO]:
        async with self._sf() as session:
            rows = await session.execute(select(Run).order_by(Run.created_at.desc()).limit(limit))
            return [run_to_dto(r) for r in rows.scalars()]

    async def get_run_detail(self, run_id: UUID) -> RunDetailDTO | None:
        async with self._sf() as session:
            return await load_run_detail(session, run_id)

    async def execute(self, run_id: UUID) -> None:
        async with self._sf() as session:
            run = await session.get(Run, run_id)
        if run is None:
            logger.error("execute called for unknown run %s", run_id)
            return
        state = _RunState(status="analyzing")
        await self._update_run(run_id, status="analyzing", started_at=datetime.now(UTC))
        await self._emit(
            run_id,
            state,
            "run_started",
            {"goal": run.goal, "case_ref": run.case_ref, "model": run.model, "max_turns": run.max_turns},
        )
        case_input = self._domain.case_input_model.model_validate(run.input)
        run_ctx = RunContext(
            run_id=run_id,
            case_ref=run.case_ref,
            case_input=case_input,
            session_factory=self._sf,
            emit=lambda event_type, payload: self._emit(run_id, state, event_type, payload),
        )
        runtime = AgentRuntime(self._domain, self._settings, self._model_factory(run_to_dto(run)))
        try:
            await asyncio.wait_for(
                self._analyze(run, run_ctx, runtime, state), timeout=self._settings.agent_run_timeout_seconds
            )
        except TimeoutError:
            await self._fail(
                run_id, state, run_ctx, "timeout", f"The run exceeded {self._settings.agent_run_timeout_seconds:g}s"
            )
        except MaxTurnsExceeded as exc:
            await self._fail(
                run_id,
                state,
                run_ctx,
                "max_turns_exceeded",
                f"The agent used all {run.max_turns} turns without finishing ({exc})",
            )
        except InvalidOutputError as exc:
            await self._fail(run_id, state, run_ctx, "invalid_output", str(exc))
        except AgentsException as exc:
            logger.exception("run %s failed inside the agent SDK", run_id)
            await self._fail(run_id, state, run_ctx, "agent_error", f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - every failure must land in the run record
            logger.exception("run %s failed", run_id)
            await self._fail(
                run_id,
                state,
                run_ctx,
                "agent_error",
                f"Unexpected {type(exc).__name__} while running the agent; see server logs",
            )

    async def _analyze(self, run: Run, run_ctx: RunContext, runtime: AgentRuntime, state: _RunState) -> None:
        prompt: str | list[Any] = self._domain.task_prompt(run.case_ref, run.goal, run_ctx.case_input)
        invocation = 1
        result = await runtime.run(run_ctx, prompt, max_turns=run.max_turns)
        output = await self._absorb(run.id, invocation, prompt, result, state)
        version = 1
        while True:
            if output.outcome == "needs_input":
                return await self._finalize(run.id, state, run_ctx, "needs_input", output)
            if output.outcome == "infeasible":
                return await self._finalize(run.id, state, run_ctx, "infeasible", output)
            proposal = output.proposal
            if proposal is None:
                raise InvalidOutputError("The agent returned proposal_ready without a proposal")
            report = await self._validate(run, run_ctx, proposal)
            if report.ok:
                await self._store_validated_proposal(run, run_ctx, proposal, report, version, state)
                return await self._finalize(run.id, state, run_ctx, "proposed", output)
            proposal_id = await self._store_proposal(run.id, version, "rejected", proposal, report, "")
            will_revise = state.revisions < self._settings.agent_max_revisions
            await self._emit(
                run.id,
                state,
                "validation_failed",
                {
                    "proposal_id": proposal_id,
                    "version": version,
                    "errors": [c.model_dump() for c in report.errors],
                    "will_revise": will_revise,
                },
            )
            if not will_revise:
                return await self._finalize(run.id, state, run_ctx, "validation_failed", output)
            state.revisions += 1
            await self._emit(
                run.id,
                state,
                "revision_started",
                {"attempt": state.revisions + 1, "reason": f"{len(report.errors)} failing check(s)"},
            )
            follow_up = {"role": "user", "content": revision_prompt(report)}
            prompt = [*result.to_input_list(), follow_up]
            invocation += 1
            result = await runtime.run(run_ctx, prompt, max_turns=run.max_turns)
            output = await self._absorb(run.id, invocation, follow_up, result, state)
            version += 1

    async def _absorb(
        self, run_id: UUID, invocation: int, prompt: Any, result: RunResult, state: _RunState
    ) -> AgentOutputBase:
        output = result.final_output
        if not isinstance(output, AgentOutputBase):
            raise InvalidOutputError(f"Unexpected final output type {type(output).__name__}")
        state.add_usage(result.context_wrapper.usage)
        await self._persist_messages(run_id, invocation, prompt, result, output)
        await self._emit(
            run_id,
            state,
            "agent_output",
            {
                "outcome": output.outcome,
                "message": output.message,
                "missing_fields": [m.model_dump() for m in output.missing_fields],
                "blocking_constraints": [b.model_dump() for b in output.blocking_constraints],
                "action_count": len(output.proposal.actions) if output.proposal else 0,
            },
        )
        return output

    async def _validate(self, run: Run, run_ctx: RunContext, proposal: ProposalBase) -> ValidationReport:
        checks = structural_checks(proposal)
        async with self._sf() as session:
            domain_report = await self._domain.validate_proposal(session, run.case_ref, run_ctx.case_input, proposal)
        return ValidationReport.from_checks([*checks, *domain_report.checks])

    async def _store_validated_proposal(
        self,
        run: Run,
        run_ctx: RunContext,
        proposal: ProposalBase,
        report: ValidationReport,
        version: int,
        state: _RunState,
    ) -> None:
        async with self._sf() as session:
            basis = await self._domain.fingerprint(session, run.case_ref, run_ctx.case_input, proposal)
            snapshot = await self._domain.snapshot(session, run.case_ref, run_ctx.case_input)
        proposal_id = await self._store_proposal(run.id, version, "validated", proposal, report, basis)
        await self._update_run(run.id, snapshot_before=snapshot, status="proposed")
        state.status = "proposed"
        await self._emit(
            run.id,
            state,
            "proposal_ready",
            {
                "proposal_id": proposal_id,
                "version": version,
                "summary": proposal.summary,
                "action_count": len(proposal.actions),
                "validation": report.model_dump(),
            },
        )

    async def _store_proposal(
        self, run_id: UUID, version: int, status: str, proposal: ProposalBase, report: ValidationReport, basis: str
    ) -> str:
        async with self._sf() as session, session.begin():
            row = Proposal(
                run_id=run_id,
                version=version,
                status=status,
                content=jsonable(proposal),
                validation=report.model_dump(),
                basis_fingerprint=basis,
            )
            session.add(row)
            await session.flush()
            return str(row.id)

    async def _persist_messages(
        self, run_id: UUID, invocation: int, prompt: Any, result: RunResult, output: AgentOutputBase
    ) -> None:
        items: list[tuple[str, str, Any]] = []
        prompt_item = {"role": "user", "content": prompt} if isinstance(prompt, str) else prompt
        items.append(("user", "message", jsonable(prompt_item)))
        for item in result.new_items:
            raw = jsonable(item.to_input_item())
            kind, role = _message_kind(raw)
            items.append((role, kind, raw))
        items.append(("assistant", "final_output", jsonable(output)))
        async with self._sf() as session, session.begin():
            current = (
                await session.execute(
                    select(func.coalesce(func.max(RunMessage.seq), 0)).where(RunMessage.run_id == run_id)
                )
            ).scalar_one()
            session.add_all(
                [
                    RunMessage(
                        run_id=run_id, seq=current + i, invocation=invocation, role=role, kind=kind, content=content
                    )
                    for i, (role, kind, content) in enumerate(items, start=1)
                ]
            )

    async def _finalize(
        self, run_id: UUID, state: _RunState, run_ctx: RunContext, status: str, output: AgentOutputBase
    ) -> None:
        state.status = status
        await self._update_run(
            run_id,
            status=status,
            outcome=output.outcome,
            agent_result=jsonable(output),
            usage=dict(state.usage),
            tool_call_count=run_ctx.stats.tool_calls,
            duration_ms=state.elapsed_ms(),
            finished_at=datetime.now(UTC),
        )
        await self._emit(
            run_id,
            state,
            "run_finished",
            {
                "outcome": output.outcome,
                "status": status,
                "duration_ms": state.elapsed_ms(),
                "tool_calls": run_ctx.stats.tool_calls,
                "usage": dict(state.usage),
            },
        )

    async def _fail(
        self, run_id: UUID, state: _RunState, run_ctx: RunContext, code: str, message: str, stage: str = "analysis"
    ) -> None:
        state.status = "failed"
        error = {"code": code, "message": message, "stage": stage}
        await self._update_run(
            run_id,
            status="failed",
            error=error,
            usage=dict(state.usage),
            tool_call_count=run_ctx.stats.tool_calls,
            duration_ms=state.elapsed_ms(),
            finished_at=datetime.now(UTC),
        )
        await self._emit(run_id, state, "run_failed", {**error, "details": {"tool_calls": run_ctx.stats.tool_calls}})

    async def _update_run(self, run_id: UUID, **values: Any) -> None:
        async with self._sf() as session, session.begin():
            await session.execute(update(Run).where(Run.id == run_id).values(**values))

    async def _emit(self, run_id: UUID, state: _RunState, event_type: str, payload: dict[str, Any]) -> None:
        await self._bus.emit(run_id, event_type, payload, run_status=state.status)


async def mark_interrupted_runs(session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> int:
    error = {
        "code": "interrupted",
        "message": "The server restarted while this run was in progress. Start a new run.",
        "stage": "restart",
    }
    async with session_factory() as session, session.begin():
        rows = (await session.execute(select(Run.id).where(Run.status.in_(IN_FLIGHT_STATUSES)))).scalars().all()
        if rows:
            await session.execute(
                update(Run)
                .where(Run.id.in_(rows))
                .values(status="interrupted", error=error, finished_at=datetime.now(UTC))
            )
    for run_id in rows:
        await bus.emit(run_id, "run_failed", {**error, "details": {}}, run_status="interrupted")
    return len(rows)

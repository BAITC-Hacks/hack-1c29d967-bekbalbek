import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.contracts import DomainModule, ExecutionError, ProposalBase
from app.core.errors import ConflictError, NotFoundError
from app.core.events import EventBus
from app.core.read_models import ApplicationDTO, application_to_dto, load_application
from app.core.serialization import jsonable
from app.db.models import ActionRecord, Application, Proposal, Run

logger = logging.getLogger(__name__)


class ApplyError(ConflictError):
    pass


class ApplyService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], domain: DomainModule, bus: EventBus) -> None:
        self._sf = session_factory
        self._domain = domain
        self._bus = bus

    async def apply(self, run_id: UUID, proposal_id: UUID, version: int) -> ApplicationDTO:
        started = time.perf_counter()
        run, proposal = await self._load_and_check(run_id, proposal_id, version)
        application_id = await self._open_application(run, proposal)
        await self._emit(
            run_id,
            "apply_started",
            {"application_id": str(application_id), "proposal_id": str(proposal.id), "version": version},
            "applying",
        )

        case_input = self._domain.case_input_model.model_validate(run.input)
        content = self._domain.proposal_model.model_validate(proposal.content)
        await self._reject_if_stale(run, proposal, application_id, case_input, content)

        results = await self._execute(run, proposal, application_id, case_input, content)
        for result in results:
            await self._emit(
                run_id,
                "action_applied",
                {
                    "action_id": result.action_id,
                    "type": result.type,
                    "summary": result.summary,
                    "result": result.result,
                },
                "applied",
            )
        return await self._verify(run, proposal, application_id, case_input, content, results, started)

    async def _load_and_check(self, run_id: UUID, proposal_id: UUID, version: int) -> tuple[Run, Proposal]:
        async with self._sf() as session:
            run = await session.get(Run, run_id)
            proposal = await session.get(Proposal, proposal_id)
        if run is None:
            raise NotFoundError("run_not_found", f"Unknown run {run_id}")
        if proposal is None or proposal.run_id != run_id or proposal.version != version:
            raise ApplyError(
                "invalid_state", "The proposal id or version does not match this run", {"expected_run_id": str(run_id)}
            )
        if proposal.status == "applied" or run.status in {"applying", "applied", "verified"}:
            raise ApplyError(
                "duplicate_apply", "This proposal is already being applied or was applied", {"status": run.status}
            )
        if run.status != "proposed":
            raise ApplyError(
                "invalid_state", f"The run is {run.status}; only proposed runs can be applied", {"status": run.status}
            )
        if proposal.status != "validated":
            raise ApplyError(
                "invalid_state", f"Proposal v{version} is {proposal.status}", {"proposal_status": proposal.status}
            )
        return run, proposal

    async def _open_application(self, run: Run, proposal: Proposal) -> UUID:
        try:
            async with self._sf() as session, session.begin():
                locked = await session.get(Run, run.id, with_for_update=True)
                if locked is not None and locked.status in {"applying", "applied", "verified"}:
                    raise ApplyError(
                        "duplicate_apply",
                        "This proposal is already being applied or was applied",
                        {"status": locked.status},
                    )
                if locked is None or locked.status != "proposed":
                    raise ApplyError("invalid_state", f"The run is {locked.status if locked else 'missing'}")
                application = Application(
                    run_id=run.id, proposal_id=proposal.id, version=proposal.version, status="applying"
                )
                session.add(application)
                await session.flush()
                locked.status = "applying"
                return application.id
        except IntegrityError as exc:
            raise ApplyError(
                "duplicate_apply",
                "This proposal is already being applied or was applied",
                {"proposal_id": str(proposal.id)},
            ) from exc

    async def _reject_if_stale(
        self, run: Run, proposal: Proposal, application_id: UUID, case_input: Any, content: ProposalBase
    ) -> None:
        async with self._sf() as session:
            current = await self._domain.fingerprint(session, run.case_ref, case_input, content)
            report = await self._domain.validate_proposal(session, run.case_ref, case_input, content)
        changed = current != proposal.basis_fingerprint
        if not changed and report.ok:
            return
        details = {"fingerprint_changed": changed, "validation": report.model_dump()}
        message = (
            "The data this proposal was based on has changed since it was made"
            if changed
            else "The proposal no longer passes validation"
        )
        async with self._sf() as session, session.begin():
            await session.execute(
                update(Application)
                .where(Application.id == application_id)
                .values(
                    status="rejected",
                    error={"code": "stale_proposal", "message": message, **details},
                    finished_at=datetime.now(UTC),
                )
            )
            await session.execute(update(Proposal).where(Proposal.id == proposal.id).values(status="stale"))
            await session.execute(update(Run).where(Run.id == run.id).values(status="proposed"))
        await self._emit(
            run.id, "apply_rejected", {"code": "stale_proposal", "message": message, "details": details}, "proposed"
        )
        raise ApplyError("stale_proposal", message, details)

    async def _execute(
        self, run: Run, proposal: Proposal, application_id: UUID, case_input: Any, content: ProposalBase
    ):
        action_keys = {a.action_id: f"{proposal.id}:{a.action_id}" for a in content.actions}
        try:
            async with self._sf() as session, session.begin():
                records = [
                    ActionRecord(
                        application_id=application_id,
                        action_key=action_keys[a.action_id],
                        action_id=a.action_id,
                        position=i,
                        type=a.type,
                        payload=jsonable(a),
                        status="applied",
                    )
                    for i, a in enumerate(content.actions)
                ]
                session.add_all(records)
                results = await self._domain.execute_actions(session, run.case_ref, case_input, content, action_keys)
                by_id = {r.action_id: r for r in results}
                for record in records:
                    result = by_id.get(record.action_id)
                    record.result = result.result if result else None
                    record.summary = result.summary if result else ""
                await session.execute(
                    update(Application).where(Application.id == application_id).values(status="applied")
                )
                await session.execute(update(Proposal).where(Proposal.id == proposal.id).values(status="applied"))
                await session.execute(update(Run).where(Run.id == run.id).values(status="applied"))
                return results
        except ExecutionError as exc:
            await self._fail(
                run.id,
                application_id,
                "execution_failed",
                f"{exc.message} ({exc.code})",
                stage="apply",
                details={"code": exc.code},
            )
        except IntegrityError as exc:
            logger.warning("integrity error while applying run %s: %s", run.id, exc)
            await self._fail(
                run.id,
                application_id,
                "execution_failed",
                "A database constraint rejected the change (duplicate action or record)",
                stage="apply",
                details={"code": "integrity_error"},
            )
        raise AssertionError("unreachable")

    async def _verify(
        self,
        run: Run,
        proposal: Proposal,
        application_id: UUID,
        case_input: Any,
        content: ProposalBase,
        results,
        started: float,
    ) -> ApplicationDTO:
        async with self._sf() as session:
            report = await self._domain.verify_outcome(session, run.case_ref, case_input, content, results)
            snapshot_after = await self._domain.snapshot(session, run.case_ref, case_input)
        status = "verified" if report.ok else "failed"
        run_values: dict[str, Any] = {
            "status": status,
            "snapshot_after": snapshot_after,
            "finished_at": datetime.now(UTC),
        }
        if not report.ok:
            run_values["error"] = {"code": "verification_failed", "message": report.summary, "stage": "verification"}
        async with self._sf() as session, session.begin():
            await session.execute(
                update(Application)
                .where(Application.id == application_id)
                .values(status=status, verification=report.model_dump(), finished_at=datetime.now(UTC))
            )
            await session.execute(update(Run).where(Run.id == run.id).values(**run_values))
        await self._emit(run.id, "verification_finished", report.model_dump(), status)
        if report.ok:
            await self._emit(
                run.id,
                "run_finished",
                {
                    "outcome": run.outcome,
                    "status": status,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "tool_calls": run.tool_call_count,
                    "usage": run.usage,
                },
                status,
            )
        else:
            await self._emit(run.id, "run_failed", {**run_values["error"], "details": {}}, status)
        async with self._sf() as session:
            application = await load_application(session, application_id)
        assert application is not None
        return application_to_dto(application)

    async def _fail(
        self, run_id: UUID, application_id: UUID, code: str, message: str, *, stage: str, details: dict[str, Any]
    ) -> None:
        error = {"code": code, "message": message, "stage": stage, **details}
        async with self._sf() as session, session.begin():
            await session.execute(
                update(Application)
                .where(Application.id == application_id)
                .values(status="failed", error=error, finished_at=datetime.now(UTC))
            )
            await session.execute(
                update(Run).where(Run.id == run_id).values(status="failed", error=error, finished_at=datetime.now(UTC))
            )
        await self._emit(run_id, "run_failed", {**error, "details": details}, "failed")
        raise ApplyError(code, message, details)

    async def _emit(self, run_id: UUID, event_type: str, payload: dict[str, Any], run_status: str) -> None:
        await self._bus.emit(run_id, event_type, payload, run_status=run_status)

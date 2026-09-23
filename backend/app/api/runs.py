from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sse_starlette import EventSourceResponse, ServerSentEvent

from app.api.deps import ServicesDep
from app.api.schemas import ApplyRequest, CreateRunRequest
from app.core.contracts import CaseNotFound
from app.core.errors import NotFoundError, TooManyRequestsError
from app.core.events import MAX_SUBSCRIBERS_PER_RUN

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", status_code=202)
async def create_run(body: CreateRunRequest, services: ServicesDep) -> dict:
    try:
        run = await services.run_service.create_run(
            case_ref=body.case_ref,
            goal=body.goal,
            input=body.input,
            max_turns=body.options.max_turns if body.options else None,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    except CaseNotFound as exc:
        raise NotFoundError("case_not_found", str(exc)) from exc
    services.registry.spawn(run.id, services.run_service.execute(run.id))
    return {"run": run}


@router.get("")
async def list_runs(services: ServicesDep, limit: int = Query(50, ge=1, le=200)) -> dict:
    return {"runs": await services.run_service.list_runs(limit=limit)}


@router.get("/{run_id}")
async def get_run(run_id: UUID, services: ServicesDep) -> dict:
    detail = await services.run_service.get_run_detail(run_id)
    if detail is None:
        raise NotFoundError("run_not_found", f"Unknown run {run_id}")
    return detail.model_dump(mode="json")


@router.get("/{run_id}/events/list")
async def list_events(run_id: UUID, services: ServicesDep, after: int = Query(0, ge=0)) -> dict:
    if await services.run_service.get_run_detail(run_id) is None:
        raise NotFoundError("run_not_found", f"Unknown run {run_id}")
    return {"events": [e.model_dump(mode="json") for e in await services.bus.replay(run_id, after)]}


@router.get("/{run_id}/events")
async def stream_events(
    run_id: UUID, request: Request, services: ServicesDep, after: int = Query(0, ge=0)
) -> EventSourceResponse:
    if await services.run_service.get_run_detail(run_id) is None:
        raise NotFoundError("run_not_found", f"Unknown run {run_id}")
    if services.bus.subscriber_count(run_id) >= MAX_SUBSCRIBERS_PER_RUN:
        raise TooManyRequestsError("too_many_streams", f"At most {MAX_SUBSCRIBERS_PER_RUN} event streams per run")
    last_event_id = request.headers.get("last-event-id", "")
    start = int(last_event_id) if last_event_id.isdigit() else after

    async def generate():
        async for event in services.bus.stream(run_id, start):
            yield ServerSentEvent(id=str(event.id), event=event.type, data=event.model_dump_json())

    return EventSourceResponse(generate(), ping=15)


@router.post("/{run_id}/apply")
async def apply_proposal(run_id: UUID, body: ApplyRequest, services: ServicesDep) -> dict:
    application = await services.apply_service.apply(run_id, body.proposal_id, body.version)
    detail = await services.run_service.get_run_detail(run_id)
    assert detail is not None
    return {"run": detail.run, "application": application}

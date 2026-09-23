from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.core.contracts import CaseNotFound
from app.domain.examples import EXAMPLES
from app.domain.models import DispatchWorker
from app.domain.seed import seed
from app.domain.service import load_case_view

router = APIRouter(prefix="/api/domain", tags=["domain"])


class WorkerPatch(BaseModel):
    capacity_hours: int | None = Field(default=None, ge=0, le=24)
    unavailable_dates: list[date] | None = Field(default=None, max_length=60)


@router.get("/examples")
async def list_examples() -> dict:
    return {"examples": [e.model_dump() for e in EXAMPLES]}


@router.get("/cases/{case_ref}")
async def get_case_view(case_ref: str, session: SessionDep) -> dict:
    try:
        return await load_case_view(session, case_ref)
    except CaseNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "case_not_found", "message": str(exc)}) from exc


@router.post("/reset")
async def reset_sample_data(session: SessionDep) -> dict:
    async with session.begin():
        counts = await seed(session)
    return {"status": "ok", "seeded": counts}


@router.patch("/workers/{worker_id}")
async def patch_worker(worker_id: str, patch: WorkerPatch, session: SessionDep) -> dict:
    async with session.begin():
        worker = await session.get(DispatchWorker, worker_id)
        if worker is None:
            raise HTTPException(
                status_code=404, detail={"code": "worker_not_found", "message": f"Unknown worker {worker_id}"}
            )
        if patch.capacity_hours is not None:
            worker.capacity_hours = patch.capacity_hours
        if patch.unavailable_dates is not None:
            worker.unavailable_dates = [d.isoformat() for d in patch.unavailable_dates]
        snapshot = {
            "id": worker.id,
            "name": worker.name,
            "capacity_hours": worker.capacity_hours,
            "unavailable_dates": list(worker.unavailable_dates),
        }
    return {"worker": snapshot}

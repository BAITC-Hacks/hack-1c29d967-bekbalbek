import secrets
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.api.deps import ServicesDep, SessionDep
from app.core.contracts import CaseNotFound
from app.domain import repo
from app.domain.examples import EXAMPLES
from app.domain.models import ActionItem, DispatchWorker, Meeting, MeetingSpeaker, Protocol
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


class SpeakerPatch(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)


def row_dict(row) -> dict:
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


@router.post("/meetings", status_code=202)
async def upload_meeting(
    session: SessionDep,
    services: ServicesDep,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    meeting_date: Annotated[date, Form()],
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".webm", ".flac"}:
        raise HTTPException(415, "Неподдерживаемый формат записи")
    meeting_id = "m-" + secrets.token_hex(12)
    media = services.settings.media_dir
    media.mkdir(parents=True, exist_ok=True)
    path = media / f"{meeting_id}{suffix}"
    size = 0
    try:
        with path.open("xb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 300 * 1024 * 1024:
                    raise HTTPException(413, "Запись превышает 300 MiB")
                target.write(chunk)
        if not size:
            raise HTTPException(422, "Запись пуста")
        meeting = Meeting(
            id=meeting_id, title=title, meeting_date=meeting_date, audio_path=str(path), status="uploaded"
        )
        session.add(meeting)
        await session.commit()
        await session.refresh(meeting)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {"meeting": jsonable_encoder(row_dict(meeting))}


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str, session: SessionDep) -> dict:
    meeting = await repo.get_meeting(session, meeting_id)
    protocol = await session.scalar(
        select(Protocol).where(Protocol.meeting_id == meeting_id).order_by(Protocol.confirmed_at.desc()).limit(1)
    )
    items = (
        list(
            await session.scalars(
                select(ActionItem).where(ActionItem.protocol_id == protocol.id).order_by(ActionItem.id)
            )
        )
        if protocol
        else []
    )
    return jsonable_encoder(
        {
            "meeting": row_dict(meeting),
            "speakers": [row_dict(row) for row in await repo.list_speakers(session, meeting_id)],
            "segments": [row_dict(row) for row in await repo.list_segments(session, meeting_id)],
            "protocol": row_dict(protocol) if protocol else None,
            "action_items": [row_dict(row) for row in items],
        }
    )


@router.post("/meetings/{meeting_id}/transcribe", status_code=202)
async def start_transcription(
    meeting_id: str, background_tasks: BackgroundTasks, session: SessionDep, services: ServicesDep
) -> dict:
    from app.domain import transcribe_job

    await repo.get_meeting(session, meeting_id)
    # Confirmed evidence must remain stable: re-transcription would replace segment ids.
    protocol = await session.scalar(select(Protocol.id).where(Protocol.meeting_id == meeting_id).limit(1))
    if protocol:
        raise HTTPException(409, "Для этой записи уже подтверждён протокол")
    claimed = await session.scalar(
        update(Meeting)
        .where(Meeting.id == meeting_id, Meeting.status != "transcribing")
        .values(status="transcribing", error=None)
        .returning(Meeting.id)
    )
    if claimed is None:
        raise HTTPException(409, "Запись уже распознаётся")
    await session.commit()
    background_tasks.add_task(transcribe_job.run, meeting_id, services.session_factory, services.settings)
    return {"meeting_id": meeting_id, "status": "transcribing"}


@router.patch("/meetings/{meeting_id}/speakers/{speaker_id}")
async def rename_speaker(meeting_id: str, speaker_id: str, patch: SpeakerPatch, session: SessionDep) -> dict:
    await repo.get_meeting(session, meeting_id)
    speaker = await session.get(MeetingSpeaker, (meeting_id, speaker_id))
    if speaker is None:
        raise HTTPException(404, "Говорящий не найден")
    name = patch.display_name.strip()
    if not name:
        raise HTTPException(422, "Имя не может быть пустым")
    speaker.display_name = name
    await session.commit()
    return {"speaker": row_dict(speaker)}

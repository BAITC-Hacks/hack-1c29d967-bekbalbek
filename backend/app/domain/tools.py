from agents import RunContextWrapper

from app.core.context import RunContext
from app.core.contracts import ToolError, ToolSpec
from app.core.serialization import jsonable
from app.domain import repo
from app.speech.deadlines import resolve


def timecode(seconds: float) -> str:
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


async def ready(session, meeting_id):
    meeting = await repo.get_meeting(session, meeting_id)
    if meeting.status != "ready":
        raise ToolError("not_ready", "Стенограмма ещё не готова")
    return meeting


async def get_meeting(ctx: RunContextWrapper[RunContext]) -> dict:
    """Прочитай название, дату, говорящих и количество сегментов готовой стенограммы. Вызови первым."""
    run_ctx = ctx.context
    async with run_ctx.session_factory() as session:
        meeting = await ready(session, run_ctx.case_ref)
        return jsonable(
            {
                "id": meeting.id,
                "title": meeting.title,
                "meeting_date": meeting.meeting_date,
                "duration_s": meeting.duration_s,
                "segment_count": len(await repo.list_segments(session, meeting.id)),
                "speakers": [
                    {"speaker_id": s.speaker_id, "display_name": s.display_name}
                    for s in await repo.list_speakers(session, meeting.id)
                ],
            }
        )


async def read_transcript(ctx: RunContextWrapper[RunContext], offset: int = 0, limit: int = 60) -> dict:
    """Прочитай сегменты стенограммы по порядку. limit=0 возвращает всю стенограмму; next_offset=null означает конец."""
    if offset < 0 or limit < 0:
        raise ToolError("invalid_arguments", "offset и limit должны быть неотрицательными")
    run_ctx = ctx.context
    async with run_ctx.session_factory() as session:
        await ready(session, run_ctx.case_ref)
        rows = await repo.list_segments(session, run_ctx.case_ref)
        speakers = {s.speaker_id: s.display_name for s in await repo.list_speakers(session, run_ctx.case_ref)}
        selected = rows[offset:] if limit == 0 else rows[offset : offset + limit]
        return {
            "segments": [
                {
                    "id": s.id,
                    "speaker": s.speaker_id,
                    "name": speakers.get(s.speaker_id, s.speaker_id),
                    "t": timecode(s.start_s),
                    "text": s.text,
                }
                for s in selected
            ],
            "total": len(rows),
            "next_offset": offset + len(selected) if offset + len(selected) < len(rows) else None,
        }


async def search_transcript(ctx: RunContextWrapper[RunContext], query: str) -> dict:
    """Найди до 20 сегментов по тексту без учёта регистра. Используй для проверки поручений и имён."""
    if not query.strip():
        raise ToolError("invalid_arguments", "Укажите текст поиска")
    data = await read_transcript(ctx, 0, 0)
    return {"segments": [s for s in data["segments"] if query.casefold() in s["text"].casefold()][:20]}


async def resolve_deadline(ctx: RunContextWrapper[RunContext], phrase: str) -> str | None:
    """Преобразуй произнесённый срок в дату ISO, отсчитывая от даты совещания. Неизвестный срок возвращает null."""
    async with ctx.context.session_factory() as session:
        meeting = await ready(session, ctx.context.case_ref)
        result = resolve(phrase, meeting.meeting_date)
        return result.isoformat() if result else None


TOOLS = [
    ToolSpec(name="get_meeting", label="Читаем данные совещания", fn=get_meeting),
    ToolSpec(name="read_transcript", label="Читаем стенограмму", fn=read_transcript),
    ToolSpec(name="search_transcript", label="Ищем подтверждение в стенограмме", fn=search_transcript),
    ToolSpec(name="resolve_deadline", label="Уточняем срок поручения", fn=resolve_deadline),
]

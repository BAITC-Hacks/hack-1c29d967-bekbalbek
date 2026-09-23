import pytest

from app.core.contracts import ToolError
from app.domain import tools
from app.domain.models import Meeting
from tests.domain.conftest import make_run_ctx


async def test_tools_read_pagination_search_and_deadline(session_factory, seeded):
    ctx = make_run_ctx(session_factory)
    assert (await tools.get_meeting(ctx))["segment_count"] == 3
    page = await tools.read_transcript(ctx, 0, 1)
    assert page["next_offset"] == 1 and page["segments"][0]["id"] == 1
    assert len((await tools.read_transcript(ctx, 0, 0))["segments"]) == 3
    assert (await tools.search_transcript(ctx, "ОТЧЁТ"))["segments"]
    assert await tools.resolve_deadline(ctx, "до пятницы") == "2026-09-25"
    assert await tools.resolve_deadline(ctx, "после встречи") is None


async def test_tools_reject_not_ready(session_factory, seeded):
    async with session_factory() as session, session.begin():
        meeting = await session.get(Meeting, "m-sample-1")
        meeting.status = "uploaded"
    with pytest.raises(ToolError, match="ещё не готова"):
        await tools.get_meeting(make_run_ctx(session_factory))


async def test_tools_reject_negative_offset(session_factory, seeded):
    with pytest.raises(ToolError):
        await tools.read_transcript(make_run_ctx(session_factory), -1)

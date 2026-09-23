from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
async def client(session_factory, tmp_path) -> AsyncIterator[AsyncClient]:
    settings = Settings(openai_model="scripted:auto", media_dir=tmp_path, stt_device="cpu")
    app = create_app(settings, session_factory=session_factory)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def upload(client, body=b"RIFF" + b"0" * 100, filename="m.wav"):
    return await client.post(
        "/api/domain/meetings",
        data={"title": "Тест", "meeting_date": "2026-09-23"},
        files={"file": (filename, body, "audio/wav")},
    )


async def test_upload_creates_meeting(client):
    response = await upload(client)
    assert response.status_code == 202, response.text
    meeting = response.json()["meeting"]
    assert meeting["status"] == "uploaded" and meeting["id"].startswith("m-")
    view = (await client.get(f"/api/domain/meetings/{meeting['id']}")).json()
    assert view["segments"] == [] and view["protocol"] is None
    assert view["meeting"]["meeting_date"] == "2026-09-23"


async def test_meeting_upload_path_is_exempt_from_body_limit(client):
    response = await upload(client, b"0" * (2 * 1024 * 1024))
    assert response.status_code == 202, response.text


async def test_upload_rejects_unsupported_and_empty_files(client):
    assert (await upload(client, filename="bad.exe")).status_code == 415
    assert (await upload(client, body=b"")).status_code == 422
    assert (await client.get("/api/domain/meetings/missing")).status_code == 404


async def test_transcription_persists_segments_and_speaker_rename(client, monkeypatch):
    from app.domain import transcribe_job
    from app.speech.align import SpokenSegment
    from app.speech.asr import Word

    monkeypatch.setattr(
        transcribe_job,
        "process_file",
        lambda *args: ([SpokenSegment(0, 1, "S1", "ru", "Коллеги", [Word(0, 1, "Коллеги", 0.9)])], 1.0),
    )
    meeting_id = (await upload(client)).json()["meeting"]["id"]
    assert (await client.post(f"/api/domain/meetings/{meeting_id}/transcribe")).status_code == 202
    view = (await client.get(f"/api/domain/meetings/{meeting_id}")).json()
    assert view["meeting"]["status"] == "ready"
    assert view["segments"][0]["text"] == "Коллеги"
    assert view["segments"][0]["words"][0]["prob"] == 0.9
    renamed = await client.patch(f"/api/domain/meetings/{meeting_id}/speakers/S1", json={"display_name": "Асхат"})
    assert renamed.status_code == 200 and renamed.json()["speaker"]["display_name"] == "Асхат"


async def test_transcription_failure_is_visible(client, monkeypatch):
    from app.domain import transcribe_job

    def fail(*args):
        raise ValueError("bad recording")

    monkeypatch.setattr(transcribe_job, "process_file", fail)
    meeting_id = (await upload(client)).json()["meeting"]["id"]
    assert (await client.post(f"/api/domain/meetings/{meeting_id}/transcribe")).status_code == 202
    view = (await client.get(f"/api/domain/meetings/{meeting_id}")).json()
    assert view["meeting"]["status"] == "failed"
    assert view["meeting"]["error"] == "bad recording"


async def test_transcribe_conflict(client, session_factory):
    from app.domain.models import Meeting

    meeting_id = (await upload(client)).json()["meeting"]["id"]
    async with session_factory() as session, session.begin():
        meeting = await session.get(Meeting, meeting_id)
        meeting.status = "transcribing"
    assert (await client.post(f"/api/domain/meetings/{meeting_id}/transcribe")).status_code == 409


async def test_replace_transcript_replaces_old_speakers(client, session_factory):
    from app.domain import repo
    from app.domain.models import MeetingSpeaker
    from app.speech.align import SpokenSegment

    meeting_id = (await upload(client)).json()["meeting"]["id"]
    async with session_factory() as session, session.begin():
        await repo.replace_transcript(session, meeting_id, [SpokenSegment(0, 1, "S1", "ru", "one", [])], 1)
        await repo.replace_transcript(session, meeting_id, [SpokenSegment(0, 2, "S2", "kk", "two", [])], 2)
    async with session_factory() as session:
        assert await session.get(MeetingSpeaker, (meeting_id, "S1")) is None
        assert len(await repo.list_segments(session, meeting_id)) == 1


@pytest.mark.models
async def test_transcribe_fills_segments(client):
    from tests.speech.conftest import FIXTURE, MODELS

    if not (MODELS / "kk-turbo-ct2" / "model.bin").exists():
        pytest.skip("model weights not downloaded")
    meeting_id = (await upload(client, FIXTURE.read_bytes())).json()["meeting"]["id"]
    assert (await client.post(f"/api/domain/meetings/{meeting_id}/transcribe")).status_code == 202
    view = (await client.get(f"/api/domain/meetings/{meeting_id}")).json()
    assert view["meeting"]["status"] == "ready", view["meeting"].get("error")
    assert "коллеги" in " ".join(s["text"] for s in view["segments"]).lower()
    assert all(s["speaker_id"].startswith("S") for s in view["segments"])

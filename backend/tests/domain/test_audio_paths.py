from types import SimpleNamespace

import pytest

from app.domain.seed import seed
from app.domain.transcribe_job import resolve_audio_path


@pytest.mark.parametrize(
    "stored",
    ["samples/sovechanie_1.mp3", "/app/samples/sovechanie_1.mp3", "/home/user/backend/samples/sovechanie_1.mp3"],
)
def test_sample_recordings_resolve_in_current_runtime(tmp_path, stored):
    settings = SimpleNamespace(samples_dir=tmp_path / "samples", media_dir=tmp_path / "media")
    assert resolve_audio_path(stored, "m-sample-1", settings) == tmp_path / "samples" / "sovechanie_1.mp3"


@pytest.mark.parametrize(
    "stored", ["media/m-recording.wav", "/app/media/m-recording.wav", "/home/user/backend/media/m-recording.wav"]
)
def test_uploaded_recordings_resolve_in_current_runtime(tmp_path, stored):
    settings = SimpleNamespace(samples_dir=tmp_path / "samples", media_dir=tmp_path / "media")
    assert resolve_audio_path(stored, "m-recording", settings) == tmp_path / "media" / "m-recording.wav"


@pytest.mark.parametrize(
    "stored",
    [
        "../samples/sovechanie_1.mp3",
        "samples/../media/m-recording.wav",
        "media/m-other.wav",
        "/app/media/m-other.wav",
        "/etc/passwd",
        "media/m-recording.exe",
        "samples/unknown.mp3",
    ],
)
def test_recording_path_cannot_access_arbitrary_files(tmp_path, stored):
    settings = SimpleNamespace(samples_dir=tmp_path / "samples", media_dir=tmp_path / "media")
    with pytest.raises(ValueError):
        resolve_audio_path(stored, "m-recording", settings)


def test_symlink_cannot_escape_media_directory(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "m-recording.wav").symlink_to(tmp_path / "private.wav")
    with pytest.raises(ValueError, match="escapes"):
        resolve_audio_path("media/m-recording.wav", "m-recording", SimpleNamespace(media_dir=media))


async def test_seed_updates_legacy_paths_without_resetting_existing_meetings():
    meetings = {
        f"m-sample-{n}": SimpleNamespace(audio_path=f"/old/samples/sovechanie_{n}.mp3", status="ready", title="edited")
        for n in (1, 2)
    }

    class Session:
        async def get(self, model, key):
            return meetings[key]

        async def flush(self):
            pass

        def add(self, value):
            raise AssertionError("Existing meetings must not be replaced")

    assert await seed(Session()) == {"meetings": 2}
    for n in (1, 2):
        meeting = meetings[f"m-sample-{n}"]
        assert meeting.audio_path == f"samples/sovechanie_{n}.mp3"
        assert meeting.status == "ready" and meeting.title == "edited"

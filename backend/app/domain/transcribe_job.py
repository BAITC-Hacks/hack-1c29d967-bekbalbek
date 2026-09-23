"""Run local speech processing off the event loop, then persist its result."""

import asyncio
import gc
import logging
import threading
from pathlib import Path

from app.speech.align import assign_speakers
from app.speech.asr import Transcriber
from app.speech.audio import duration_seconds, load_16k
from app.speech.diarize import Diarizer

log = logging.getLogger(__name__)
_processing_lock = threading.Lock()


_SAMPLE_FILES = {"sovechanie_1.mp3", "sovechanie_2.mp3", "mixed-ru-kk-en-1.m4a", "mixed-ru-kk-en-2.m4a"}
_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".webm", ".flac"}


def resolve_audio_path(stored_path: str, meeting_id: str, settings) -> Path:
    """Map portable or legacy recording paths to this runtime's mounted folders."""
    stored = Path(stored_path)
    name = stored.name
    if name in _SAMPLE_FILES and (stored.is_absolute() or stored.parts == ("samples", name)):
        base = Path(settings.samples_dir).resolve()
    elif (
        stored.stem == meeting_id
        and stored.suffix.lower() in _AUDIO_SUFFIXES
        and (stored.is_absolute() or stored.parts == ("media", name))
    ):
        base = Path(settings.media_dir).resolve()
    else:
        raise ValueError("Recording path is outside the meeting's media storage")
    resolved = (base / name).resolve()
    if resolved.parent != base:
        raise ValueError("Recording path escapes its media storage")
    return resolved


def transcriber(models_dir: Path, device: str) -> Transcriber:
    return Transcriber(models_dir, device)


def process_file(path: Path, models_dir: Path, device: str, threshold: float, hint_names: list[str] | None = None):
    # One recording at a time bounds RAM/VRAM and avoids simultaneous model loads.
    with _processing_lock:
        pcm = load_16k(path)
        model = transcriber(models_dir, device)
        try:
            segments = model.transcribe(pcm, hint_names)
        finally:
            del model
            gc.collect()
        turns = Diarizer(models_dir, threshold).turns(pcm)
        return assign_speakers(segments, turns), duration_seconds(pcm)


async def run(meeting_id: str, session_factory, settings) -> None:
    from app.domain import repo

    try:
        async with session_factory() as session:
            meeting = await repo.get_meeting(session, meeting_id)
            path = resolve_audio_path(meeting.audio_path, meeting_id, settings)
            await repo.set_status(session, meeting_id, "transcribing")
            await session.commit()
        spoken, duration = await asyncio.to_thread(
            process_file, path, settings.models_dir, settings.stt_device, settings.diarize_threshold
        )
        if not spoken:
            raise ValueError("В записи не удалось распознать речь")
        async with session_factory() as session:
            await repo.replace_transcript(session, meeting_id, spoken, duration)
            await repo.set_status(session, meeting_id, "ready")
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("transcription failed for %s", meeting_id)
        async with session_factory() as session:
            await repo.set_status(session, meeting_id, "failed", error=str(exc)[:500])
            await session.commit()

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
            path = Path(meeting.audio_path)
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

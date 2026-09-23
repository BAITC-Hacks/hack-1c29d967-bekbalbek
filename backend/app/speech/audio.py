from pathlib import Path

import numpy as np
from faster_whisper.audio import decode_audio

SAMPLE_RATE = 16000


def load_16k(path: Path) -> np.ndarray:
    """Any format ffmpeg/PyAV reads (mp3, wav, m4a, mp4) -> float32 mono 16 kHz."""
    return np.asarray(decode_audio(str(path), sampling_rate=SAMPLE_RATE), dtype=np.float32)


def duration_seconds(pcm: np.ndarray) -> float:
    return float(len(pcm)) / SAMPLE_RATE

"""Two Whisper models, one per language family, chosen per VAD window from a constrained language ID."""
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.vad import VadOptions, get_speech_timestamps

from app.speech.audio import SAMPLE_RATE
from app.speech.cuda import preload_cuda_libs

log = logging.getLogger(__name__)

RU_MODEL_ID = "deepdml/faster-whisper-large-v3-turbo-ct2"
ALLOWED_LANGS = ("ru", "kk", "en")
FALLBACK_LANG = "ru"
MIN_LANG_PROB = 0.3
LEAD_RATIO = 2.0
LID_SECONDS = 10
WINDOW_MAX_S = 10.0
MIN_LID_S = 5.0
NO_SPEECH_MAX = 0.6
HALLUCINATIONS = ("субтитры", "продолжение следует", "редактор субтитров", "amara.org", "thank you for watching", "подписывайтесь")
COMMON_KWARGS = dict(beam_size=5, word_timestamps=True, condition_on_previous_text=False, vad_filter=False, temperature=[0.0, 0.2, 0.4], compression_ratio_threshold=2.4)
KK_KWARGS = dict(no_repeat_ngram_size=3, repetition_penalty=1.15)


@dataclass
class Word:
    start: float
    end: float
    text: str
    prob: float


@dataclass
class Segment:
    start: float
    end: float
    text: str
    language: str
    words: list[Word] = field(default_factory=list)
    no_speech_prob: float = 0.0


class Transcriber:
    def __init__(self, models_dir: Path, device: str = "auto") -> None:
        self.models_dir = models_dir
        self.device, self.compute_type = self._pick(device)
        self._ru: WhisperModel | None = None
        self._kk: WhisperModel | None = None
        self.language_windows: list[tuple[float, float, str, float]] = []

    @staticmethod
    def _pick(device: str) -> tuple[str, str]:
        if device == "cpu":
            return "cpu", "int8"
        if device not in {"auto", "cuda"}:
            raise ValueError("device must be auto, cuda or cpu")
        if not preload_cuda_libs():
            return "cpu", "int8"
        if device == "cuda":
            return "cuda", "int8_float16"
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "int8_float16"
        except Exception:  # noqa: BLE001
            pass
        return "cpu", "int8"

    def _load(self, name_or_path: str) -> WhisperModel:
        kwargs = dict(device=self.device, compute_type=self.compute_type, local_files_only=True)
        if self.device == "cpu":
            kwargs["cpu_threads"] = 8
        try:
            return WhisperModel(name_or_path, **kwargs)
        except Exception:  # noqa: BLE001  CUDA missing at runtime: fall back to CPU
            self.device, self.compute_type = "cpu", "int8"
            return WhisperModel(name_or_path, device="cpu", compute_type="int8", cpu_threads=8, local_files_only=True)

    @property
    def ru(self) -> WhisperModel:
        if self._ru is None:
            local = self.models_dir / "ru-turbo-ct2"
            self._ru = self._load(str(local) if (local / "model.bin").exists() else RU_MODEL_ID)
        return self._ru

    @property
    def kk(self) -> WhisperModel:
        if self._kk is None:
            local = self.models_dir / "kk-turbo-ct2"
            if (local / "model.bin").is_file():
                self._kk = self._load(str(local))
            else:
                log.warning("Kazakh model weights are missing; using the local multilingual Whisper model for Kazakh speech")
                self._kk = self.ru
        return self._kk

    def windows(self, pcm: np.ndarray) -> list[tuple[int, int]]:
        opts = VadOptions(min_silence_duration_ms=500, speech_pad_ms=200, max_speech_duration_s=WINDOW_MAX_S)
        spans = [(s["start"], s["end"]) for s in get_speech_timestamps(pcm, opts)]
        if not spans:
            return [(0, len(pcm))]
        # glue windows shorter than MIN_LID_S to their predecessor so language ID has enough audio
        merged: list[tuple[int, int]] = []
        for start, end in spans:
            if merged and (end - start) < MIN_LID_S * SAMPLE_RATE and (end - merged[-1][0]) <= WINDOW_MAX_S * SAMPLE_RATE:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))
        return merged

    def detect(self, pcm: np.ndarray) -> tuple[str, float]:
        """Language of a window from its first 10 s, restricted to ru/kk/en. The turbo model is the judge."""
        _, _, probs = self.ru.detect_language(audio=pcm[: LID_SECONDS * SAMPLE_RATE])
        table = {lang: p for lang, p in probs if lang in ALLOWED_LANGS}
        ranked = sorted(table.items(), key=lambda kv: kv[1], reverse=True)
        if not ranked:
            return FALLBACK_LANG, 0.0
        (lang, p), runner = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0.0)
        if p >= MIN_LANG_PROB or (runner > 0 and p / runner >= LEAD_RATIO):
            return lang, p
        return FALLBACK_LANG, p

    def transcribe(self, pcm: np.ndarray, hint_names: list[str] | None = None) -> list[Segment]:
        out: list[Segment] = []
        self.language_windows = []
        if len(pcm) == 0 or not np.any(pcm):
            return out
        for start, end in self.windows(pcm):
            chunk = pcm[start:end]
            lang, prob = self.detect(chunk)
            offset = start / SAMPLE_RATE
            self.language_windows.append((offset, end / SAMPLE_RATE, lang, prob))
            if lang == "kk":
                segs, _ = self.kk.transcribe(chunk, language="kk", **COMMON_KWARGS, **KK_KWARGS)
            else:
                prompt = ", ".join(hint_names) if hint_names else None
                segs, _ = self.ru.transcribe(chunk, language=lang, initial_prompt=prompt, **COMMON_KWARGS)
            for s in segs:
                text = s.text.strip()
                if not text or s.no_speech_prob > NO_SPEECH_MAX or any(h in text.lower() for h in HALLUCINATIONS):
                    continue
                if lang == "kk":
                    text = text[:1].upper() + text[1:]  # the Kazakh model emits lowercase; do not invent punctuation
                words = [Word(offset + w.start, offset + w.end, w.word.strip(), w.probability) for w in (s.words or [])]
                out.append(Segment(offset + s.start, offset + s.end, text, lang, words, s.no_speech_prob))
        return out

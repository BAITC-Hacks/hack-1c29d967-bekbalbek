import pytest

from app.speech import guard
from app.speech.asr import Transcriber
from app.speech.audio import load_16k
from tests.speech.conftest import FIXTURE, MODELS, needs_models


@pytest.mark.models
@needs_models
def test_russian_clip_is_transcribed_with_words():
    guard.install()
    before = guard.status()["blocked_external_connections"]
    pcm = load_16k(FIXTURE)
    segments = Transcriber(MODELS, device="cpu").transcribe(pcm)
    text = " ".join(s.text for s in segments).lower()
    assert "коллеги" in text
    assert all(s.language == "ru" for s in segments)
    assert all(w.end >= w.start for s in segments for w in s.words)
    assert segments[0].words, "word timestamps are required for speaker alignment"
    assert guard.status()["blocked_external_connections"] == before


def test_routes_windows_to_local_language_model_and_offsets_words(monkeypatch):
    from types import SimpleNamespace

    import numpy as np

    calls = []

    class FakeModel:
        def transcribe(self, pcm, **kwargs):
            calls.append(kwargs)
            word = SimpleNamespace(start=0.2, end=0.8, word=" сөз", probability=0.9)
            segment = SimpleNamespace(start=0.2, end=0.8, text=" сөз", words=[word], no_speech_prob=0.0)
            return iter([segment]), None

    stt = Transcriber(MODELS, device="cpu")
    stt._ru, stt._kk = FakeModel(), FakeModel()
    monkeypatch.setattr(stt, "windows", lambda pcm: [(0, 16000), (16000, 32000)])
    languages = iter([("ru", 0.98), ("kk", 0.94)])
    monkeypatch.setattr(stt, "detect", lambda pcm: next(languages))
    result = stt.transcribe(np.ones(32000, dtype=np.float32), ["Асхат"])
    assert [s.language for s in result] == ["ru", "kk"]
    assert result[1].words[0].start == 1.2
    assert [call["language"] for call in calls] == ["ru", "kk"]
    assert calls[0]["initial_prompt"] == "Асхат"
    assert "initial_prompt" not in calls[1]
    assert stt.language_windows == [(0.0, 1.0, "ru", 0.98), (1.0, 2.0, "kk", 0.94)]


def test_cuda_model_load_failure_retries_cpu_int8(monkeypatch):
    calls = []

    def load(path, **kwargs):
        calls.append(kwargs)
        if kwargs["device"] == "cuda":
            raise RuntimeError("CUDA unavailable")
        return object()

    monkeypatch.setattr("app.speech.asr.WhisperModel", load)
    stt = Transcriber(MODELS, device="cpu")
    stt.device, stt.compute_type = "cuda", "int8_float16"
    stt._load("local-model")
    assert [call["device"] for call in calls] == ["cuda", "cpu"]
    assert calls[-1]["compute_type"] == "int8"
    assert all(call["local_files_only"] for call in calls)


def test_language_detection_is_constrained_and_uncertainty_falls_back():
    from types import SimpleNamespace

    import numpy as np

    stt = Transcriber(MODELS, device="cpu")
    stt._ru = SimpleNamespace(detect_language=lambda **_: ("tr", 0.8, [("tr", 0.8), ("kk", 0.1), ("ru", 0.09)]))
    assert stt.detect(np.ones(16000))[0] == "ru"
    stt._ru = SimpleNamespace(detect_language=lambda **_: ("kk", 0.7, [("kk", 0.7), ("ru", 0.2)]))
    assert stt.detect(np.ones(16000)) == ("kk", 0.7)

import numpy as np
import pytest

from app.speech import guard
from app.speech.audio import load_16k
from app.speech.diarize import Diarizer
from tests.speech.conftest import FIXTURE, MODELS, needs_models


@pytest.mark.models
@needs_models
def test_turns_cover_speech_and_are_sorted():
    guard.install()
    before = guard.status()["blocked_external_connections"]
    turns = Diarizer(MODELS, threshold=0.7).turns(load_16k(FIXTURE))
    assert turns, "at least one turn expected"
    assert turns == sorted(turns, key=lambda t: t.start)
    assert all(t.speaker.startswith("S") for t in turns)
    assert guard.status()["blocked_external_connections"] == before


def test_diarizer_returns_empty_on_garbage_input():
    assert Diarizer(MODELS, threshold=0.7).turns(np.zeros(100, dtype=np.float32)) == []

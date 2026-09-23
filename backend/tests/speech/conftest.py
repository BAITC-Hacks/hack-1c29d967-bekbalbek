from pathlib import Path

import pytest

MODELS = Path(__file__).resolve().parents[2] / "models"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "meeting_10s.wav"
models_present = (MODELS / "kk-turbo-ct2" / "model.bin").exists() and (MODELS / "vad" / "silero_vad.onnx").exists()
needs_models = pytest.mark.skipif(not models_present, reason="model weights not downloaded")

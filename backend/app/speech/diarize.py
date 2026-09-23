"""Offline speaker diarization with sherpa-onnx (pyannote segmentation + ERes2Net embeddings), CPU only."""
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Turn:
    start: float
    end: float
    speaker: str


class Diarizer:
    def __init__(self, models_dir: Path, threshold: float = 0.7, num_clusters: int = -1) -> None:
        self.seg = models_dir / "diarization" / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"
        self.emb = models_dir / "diarization" / "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
        self.threshold, self.num_clusters = threshold, num_clusters

    def available(self) -> bool:
        return self.seg.exists() and self.emb.exists()

    def turns(self, pcm: np.ndarray) -> list[Turn]:
        if not self.available() or len(pcm) < 16000:
            return []
        try:
            import sherpa_onnx

            config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
                segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                    pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(self.seg))
                ),
                embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(self.emb), num_threads=4, provider="cpu"),
                clustering=sherpa_onnx.FastClusteringConfig(num_clusters=self.num_clusters, threshold=self.threshold),
                min_duration_on=0.3,
                min_duration_off=0.5,
            )
            sd = sherpa_onnx.OfflineSpeakerDiarization(config)
            result = sd.process(pcm.astype(np.float32)).sort_by_start_time()
            return [Turn(float(r.start), float(r.end), f"S{int(r.speaker) + 1}") for r in result]
        except Exception as exc:  # noqa: BLE001
            log.warning("diarization failed, continuing with a single speaker: %s", exc)
            return []

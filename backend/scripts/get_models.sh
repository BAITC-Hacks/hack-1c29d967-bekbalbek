#!/usr/bin/env sh
# Install public local speech models. Runtime does not contact model hosts.
set -eu
cd "$(dirname "$0")/.."
mkdir -p models/diarization models/vad
if [ ! -f models/vad/silero_vad.onnx ]; then
  curl -fL -o models/vad/silero_vad.onnx https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx
fi
if [ ! -f models/diarization/sherpa-onnx-pyannote-segmentation-3-0/model.onnx ]; then
  archive=$(mktemp)
  trap 'rm -f "$archive"' EXIT
  curl -fL -o "$archive" https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2
  tar -xjf "$archive" -C models/diarization
fi
if [ ! -f models/diarization/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx ]; then
  curl -fL -o models/diarization/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx
fi
uv run python -c "from faster_whisper.utils import download_model; download_model('deepdml/faster-whisper-large-v3-turbo-ct2', output_dir='models/ru-turbo-ct2')"
if [ ! -f models/kk-turbo-ct2/model.bin ]; then
  echo 'Kazakh model missing: place the CT2 model folder at backend/models/kk-turbo-ct2 (model.bin, config.json, tokenizer.json, preprocessor_config.json).' >&2
  exit 1
fi
echo 'models ready'

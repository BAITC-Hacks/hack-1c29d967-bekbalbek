#!/usr/bin/env bash
# Configure a 16k context for an already installed local Qwen model.
set -euo pipefail

model="${1:-qwen3.5:4b}"
if [[ "$#" -gt 1 ]]; then
  echo "Usage: $0 [qwen3.5:4b|qwen3:4b-instruct-2507-q4_K_M]" >&2
  exit 2
fi
case "$model" in
  qwen3.5:4b|qwen3:4b-instruct-2507-q4_K_M) ;;
  *) echo "Unsupported model: $model" >&2; exit 2 ;;
esac

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is required. Install it and load the selected Qwen model first." >&2
  exit 1
fi
# Ignore any inherited remote host: model administration stays on this machine.
export OLLAMA_HOST=http://localhost:11434
if ! ollama show "$model" >/dev/null; then
  echo "Local model $model is unavailable. This command does not download weights." >&2
  exit 1
fi

alias_name="protokol-$model"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
model_file="$(mktemp "$script_dir/.ollama-context.XXXXXX")"
trap 'rm -f -- "$model_file"' EXIT
printf 'FROM %s\nPARAMETER num_ctx 16384\n' "$model" > "$model_file"
ollama create "$alias_name" -f "$model_file"
printf '\nLocal model configured with a 16384-token context.\nexport OPENAI_MODEL=%s\n' "$alias_name"

#!/bin/sh
# One-time setup of the MeloTTS env used by `pipeline tts` (content/tts/, Python 3.10, own uv.lock).
# Needs: uv, ffmpeg (brew install ffmpeg). Downloads ~2 GB (torch, unidic, model weights).
set -eu
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found: brew install ffmpeg" >&2; exit 1; }
uv sync
[ -f .venv/lib/python3.10/site-packages/unidic/dicdir/dicrc ] || uv run python -m unidic download
# Load the Korean model once so the weights + BERT are cached before the first real run.
wav="$(mktemp -d)/warmup.wav"
printf '[{"text": "안녕하세요", "wav": "%s"}]' "$wav" |
	uv run python synth.py --language KR --speaker KR --speed 0.9
rm -f "$wav"
echo "TTS env ready. Try: cd .. && uv run pipeline tts ko-en --sample 5"

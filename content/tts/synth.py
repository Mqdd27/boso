"""Run inside the content/tts env: read [{"text", "wav"}] JSON on stdin, write one WAV per job.

Called by `pipeline tts` (content/pipeline/tts.py). The model loads once per batch.
Usage: synth.py --language KR --speaker KR --speed 0.9 < jobs.json
"""

import argparse
import json
import os
import sys
import types
import warnings

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # quiet a fork warning from transformers
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")  # librosa 0.9.1

# MeloTTS imports its Japanese module (which builds a MeCab.Tagger) even for Korean. mecab-python3
# is left out on purpose (see pyproject.toml), so give that import a stub; it is never used.
sys.modules.setdefault("MeCab", types.SimpleNamespace(Tagger=lambda *a, **k: None))

from melo.api import TTS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True)
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--speed", type=float, required=True)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    jobs = json.load(sys.stdin)
    model = TTS(language=args.language, device=args.device)
    speaker = model.hps.data.spk2id[args.speaker]
    for n, job in enumerate(jobs, 1):
        model.tts_to_file(job["text"], speaker, job["wav"], speed=args.speed, quiet=True)
        print(f"{n}/{len(jobs)} {job['text']}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

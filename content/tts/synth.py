"""Run inside the content/tts env: read [{"text", "wav", "tone"?}] JSON on stdin, write WAVs.

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

# Pitch of the four tones on Chao's 1–5 scale, (position in the voiced part, level). MeloTTS says
# single syllables with unreliable tones (tone 2 often falls), so a job with "tone" gets this
# contour drawn onto it with WORLD (pyworld): same voice and timing, textbook pitch.
SHAPES = {
    1: [(0, 5), (1, 5)],
    2: [(0, 3), (0.2, 3), (1, 5)],
    3: [(0, 2), (0.5, 1), (1, 4)],
    4: [(0, 5), (1, 1)],
}
SEMITONES_PER_LEVEL = 2.5  # 5 levels over 10 semitones, centred on the voice's median pitch


def reshape(wav: str, tone: int) -> None:
    import numpy as np
    import pyworld
    import soundfile

    x, sr = soundfile.read(wav)
    x = np.ascontiguousarray(x.astype(np.float64))
    f0, t = pyworld.harvest(x, sr)
    sp = pyworld.cheaptrick(x, f0, t, sr)
    ap = pyworld.d4c(x, f0, t, sr)
    voiced = np.flatnonzero(f0 > 0)
    if len(voiced) < 2:
        return
    first, last = voiced[0], voiced[-1]
    base = float(np.median(f0[voiced]))
    pos = (np.arange(first, last + 1) - first) / (last - first)
    xs, levels = zip(*SHAPES[tone], strict=True)
    semis = (np.interp(pos, xs, levels) - 3) * SEMITONES_PER_LEVEL
    f0[first : last + 1] = base * 2 ** (semis / 12)
    f0[:first] = 0
    f0[last + 1 :] = 0
    soundfile.write(wav, pyworld.synthesize(f0, sp, ap, sr), sr)


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
        if job.get("tone"):
            reshape(job["wav"], job["tone"])
        print(f"{n}/{len(jobs)} {job['text']}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

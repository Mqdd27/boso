"""`pipeline tts <course>`: pre-generated audio, MeloTTS → ffmpeg → Opus, cached by settings.

MeloTTS lives in its own env (content/tts/, torch + old pins) and runs via subprocess, so the
pipeline and CI never install it. Audio is a build artefact: it goes to cache/tts/ here and into
dist/ via `pipeline pack`, never into courses/.

Settings (change one and only the affected files are rebuilt, the cache key covers them all):
- MeloTTS-Korean (KR) / -Chinese (ZH), speed 0.9: a touch slower than default, clearer for learners.
- ffmpeg: trim leading/trailing silence, loudnorm to -16 LUFS (same loudness for every word),
  mono Opus 32 kbps in VoIP mode. 24 kbps starts to smear Korean aspirated consonants
  (ㅋ/ㅌ/ㅊ); 32 kbps keeps a word at ~3–6 KB.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pipeline.validate import validate_course_dir

CONTENT = Path(__file__).resolve().parents[1]
TTS_ENV = CONTENT / "tts"
CACHE = CONTENT / "cache" / "tts"
SAMPLES = CONTENT / "cache" / "tts-sample"

VOICES = {
    "ko": {"model": "myshell-ai/MeloTTS-Korean", "language": "KR", "speaker": "KR"},
    # Pinyin script items are read from readings.yaml (a character per syllable: ma3 → 马).
    "zh": {"model": "myshell-ai/MeloTTS-Chinese", "language": "ZH", "speaker": "ZH"},
}
SPEED = 0.9
TRIM = "silenceremove=start_periods=1:start_threshold=-50dB"
FILTER = f"{TRIM},areverse,{TRIM},areverse,loudnorm=I=-16:TP=-1.5:LRA=11"
# MeloTTS-Chinese comes out ~20 dB quieter than Korean (peak around -34 dB): without gain the
# -50 dB silence trim eats most of a syllable.
GAIN = {"zh": "volume=20dB"}
ENCODE = ["-ac", "1", "-c:a", "libopus", "-b:a", "32k", "-application", "voip"]

Synth = Callable[[str, list[dict]], None]  # (target language, [{text, wav, tone?}]) → WAVs
Encode = Callable[[Path, Path, str], None]  # (wav, opus, ffmpeg filter)


@dataclass
class Job:
    item_id: str
    text: str  # what is read aloud: item.text, or readings.yaml
    key: str
    tone: int | None = None  # a single Mandarin syllable: its pitch is redrawn (tts/synth.py)


@dataclass
class Report:
    made: list[str] = field(default_factory=list)
    cached: int = 0
    seconds: float = 0.0
    files: list[Path] = field(default_factory=list)


def audio_path(item_id: str) -> str:
    """Pack path of an item's audio: ko.w.annyeong → ko/w.annyeong.opus."""
    lang, _, rest = item_id.partition(".")
    return f"{lang}/{rest}.opus"


def audio_filter(lang: str) -> str:
    return ",".join(f for f in (GAIN.get(lang), FILTER) if f)


def settings(lang: str) -> dict:
    return {**VOICES[lang], "speed": SPEED, "filter": audio_filter(lang), "encode": ENCODE}


# Bump when tts/synth.py's tone SHAPES change, so reshaped syllables are made again.
RESHAPE = "world-v1"


def tone_of(item: dict) -> int | None:
    """Tone 1–4 of a single-syllable item (ma3 → 3); None otherwise (also neutral ma5)."""
    m = re.fullmatch(r"[a-zü]+([1-4])", item.get("tones", ""))
    return int(m[1]) if m else None


def cache_key(text: str, lang: str, tone: int | None = None) -> str:
    extra = {"tone": tone, "reshape": RESHAPE} if tone else {}
    blob = json.dumps({"text": text, **settings(lang), **extra}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def readings(course_dir: Path) -> dict[str, str]:
    """Optional readings.yaml ({item id: text to read}) for items read differently from their
    text, e.g. a Hangul letter ㄱ read as 기역. Pipeline-only: never part of the pack."""
    path = course_dir / "readings.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def jobs(course_dir: Path, lang: str) -> list[Job]:
    errors, units = validate_course_dir(course_dir)
    if errors:
        raise ValueError("\n".join(errors))
    read = readings(course_dir)
    out = []
    for unit in units:
        for item in unit["items"]:
            text = read.get(item["id"], item["text"])
            tone = tone_of(item)
            out.append(Job(item["id"], text, cache_key(text, lang, tone), tone))
    return out


def cached(job: Job, cache: Path = CACHE) -> Path | None:
    path = cache / f"{job.key}.opus"
    return path if path.is_file() else None


def check_tools() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found. Install it: brew install ffmpeg")
    if not (TTS_ENV / ".venv").is_dir():
        raise RuntimeError("MeloTTS env not set up. Run: content/tts/setup.sh")


def run_melo(lang: str, batch: list[dict]) -> None:
    voice = VOICES[lang]
    subprocess.run(
        ["uv", "run", "--project", str(TTS_ENV), "python", str(TTS_ENV / "synth.py"),
         "--language", voice["language"], "--speaker", voice["speaker"], "--speed", str(SPEED)],
        input=json.dumps(batch, ensure_ascii=False),
        text=True,
        check=True,
        cwd=TTS_ENV,
    )  # fmt: skip


def run_ffmpeg(wav: Path, opus: Path, af: str = FILTER) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", af, *ENCODE, str(opus)],
        check=True,
    )


def generate(
    course_id: str,
    courses: Path,
    sample: int | None = None,
    only: str | None = None,
    synth: Synth = run_melo,
    encode: Encode = run_ffmpeg,
    cache: Path = CACHE,
    samples: Path = SAMPLES,
) -> Report:
    """Make the missing audio of a course. `only` remakes one item, `sample` the first N items
    (also copied to `samples` under readable names, to listen to before a full run)."""
    start = time.monotonic()
    course_dir = courses / course_id
    lang = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))["target"]
    todo = jobs(course_dir, lang)
    if only:
        todo = [j for j in todo if j.item_id == only]
        if not todo:
            raise ValueError(f"no item {only} in {course_id}")
        (cache / f"{todo[0].key}.opus").unlink(missing_ok=True)
    if sample:
        todo = todo[:sample]
    report = Report()
    missing = list({j.key: j for j in todo if not cached(j, cache)}.values())  # dedupe same text
    report.cached = len(todo) - len(missing)
    if missing:
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            wavs = {j.key: Path(tmp) / f"{j.key}.wav" for j in missing}
            synth(
                lang,
                [{"text": j.text, "wav": str(wavs[j.key])} | ({"tone": j.tone} if j.tone else {})
                 for j in missing],
            )  # fmt: skip
            for j in missing:
                part = cache / f"{j.key}.part.opus"  # never leave a half-written cache entry
                encode(wavs[j.key], part, audio_filter(lang))
                part.rename(cache / f"{j.key}.opus")
                report.made.append(j.item_id)
                print(f"made {j.item_id} ({j.text})", file=sys.stderr)
    if sample:
        shutil.rmtree(samples, ignore_errors=True)
        samples.mkdir(parents=True)
        for j in todo:
            shutil.copyfile(cache / f"{j.key}.opus", samples / f"{j.item_id}.opus")
    report.files = [cache / f"{j.key}.opus" for j in todo]
    report.seconds = time.monotonic() - start
    return report

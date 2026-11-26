import json
from pathlib import Path

import pytest
import yaml

from pipeline import tts
from pipeline.pack import pack
from pipeline.validate import check

ITEMS = [("ko.w.annyeong", "안녕", "annyeong", "hello"), ("ko.w.ne", "네", "ne", "yes")]


@pytest.fixture
def courses(tmp_path) -> Path:
    course = tmp_path / "courses" / "ko-en"
    (course / "units").mkdir(parents=True)
    meta = {"id": "ko-en", "target": "ko", "glosses": ["en", "id"], "levels": ["topik1"],
            "version": "0.0.1", "units": ["units/010-hi.yaml"]}  # fmt: skip
    unit = {
        "id": "ko-010-hi",
        "title": {"en": "Hi"},
        "level": "topik1",
        "items": [
            {
                "id": i,
                "type": "word",
                "text": t,
                "roman": r,
                "gloss": {"en": g},
                "source": "krdict",
                "license": "CC BY-SA 2.0 KR",
                "review": "needs_review",
            }
            for i, t, r, g in ITEMS
        ],  # fmt: skip
    }
    (course / "course.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    (course / "units" / "010-hi.yaml").write_text(yaml.safe_dump(unit, allow_unicode=True))
    return tmp_path / "courses"


class Fake:
    """Stub MeloTTS + ffmpeg: a WAV holds its text, the opus holds the WAV."""

    def __init__(self):
        self.read: list[str] = []

    def synth(self, lang: str, batch: list[dict]) -> None:
        for job in batch:
            self.read.append(job["text"])
            Path(job["wav"]).write_text(job["text"], encoding="utf-8")

    def encode(self, wav: Path, opus: Path, af: str = "") -> None:
        opus.write_text(f"opus:{wav.read_text(encoding='utf-8')}", encoding="utf-8")


def run(courses, tmp_path, fake, **kw):
    return tts.generate("ko-en", courses, synth=fake.synth, encode=fake.encode,
                        cache=tmp_path / "tts", samples=tmp_path / "samples", **kw)  # fmt: skip


def test_audio_path_follows_the_item_id():
    assert tts.audio_path("ko.w.annyeong") == "ko/w.annyeong.opus"
    assert tts.audio_path("ko.w.bae-12345") == "ko/w.bae-12345.opus"


def test_cache_key_covers_text_and_every_setting(monkeypatch):
    base = tts.cache_key("안녕", "ko")
    assert tts.cache_key("안녕", "ko") == base
    assert tts.cache_key("네", "ko") != base
    monkeypatch.setattr(tts, "SPEED", 1.0)
    assert tts.cache_key("안녕", "ko") != base
    monkeypatch.undo()
    monkeypatch.setattr(tts, "ENCODE", [*tts.ENCODE[:-1], "audio"])
    assert tts.cache_key("안녕", "ko") != base


def test_generate_caches_and_only_remakes_what_changed(courses, tmp_path):
    fake = Fake()
    first = run(courses, tmp_path, fake)
    assert first.made == ["ko.w.annyeong", "ko.w.ne"] and first.cached == 0
    assert fake.read == ["안녕", "네"]

    again = run(courses, tmp_path, fake)
    assert again.made == [] and again.cached == 2

    only = run(courses, tmp_path, fake, only="ko.w.ne")
    assert only.made == ["ko.w.ne"]
    assert not list((tmp_path / "tts").glob("*.part.opus"))


def test_readings_change_what_is_read(courses, tmp_path):
    (courses / "ko-en" / "readings.yaml").write_text("ko.w.ne: 네에\n", encoding="utf-8")
    fake = Fake()
    run(courses, tmp_path, fake)
    assert fake.read == ["안녕", "네에"]


def test_sample_writes_readable_copies(courses, tmp_path):
    report = run(courses, tmp_path, Fake(), sample=1)
    assert report.made == ["ko.w.annyeong"]
    assert [p.name for p in (tmp_path / "samples").iterdir()] == ["ko.w.annyeong.opus"]


def test_unknown_only_id_fails(courses, tmp_path):
    with pytest.raises(ValueError, match="no item"):
        run(courses, tmp_path, Fake(), only="ko.w.nope")


def test_pack_adds_audio_only_where_the_file_exists(courses, tmp_path):
    run(courses, tmp_path, Fake(), sample=1)  # audio for 안녕 only
    out, audio, items = pack("ko-en", courses, tmp_path / "dist", tts_cache=tmp_path / "tts")
    assert (audio, items) == (1, 2)
    course = json.loads((out / "course.json").read_text(encoding="utf-8"))
    hi, ne = course["units"][0]["items"]
    assert hi["audio"] == "ko/w.annyeong.opus" and "audio" not in ne
    assert (out / "audio" / "ko" / "w.annyeong.opus").read_text() == "opus:안녕"
    assert check(course, "course", "course.json") == []
    assert "audio" not in (courses / "ko-en" / "units" / "010-hi.yaml").read_text()


def test_pack_without_audio_is_valid_and_drops_stale_files(courses, tmp_path):
    stale = tmp_path / "dist" / "ko-en" / "audio" / "ko" / "w.old.opus"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    out, audio, _ = pack("ko-en", courses, tmp_path / "dist", tts_cache=tmp_path / "tts")
    assert audio == 0 and not stale.exists()
    course = json.loads((out / "course.json").read_text(encoding="utf-8"))
    assert check(course, "course", "course.json") == []


def test_single_mandarin_syllables_get_their_tone_redrawn():
    assert [tts.tone_of({"tones": t}) for t in ["ma3", "ni3 hao3", "ma5", "nü3"]] == [
        3,
        None,
        None,
        3,
    ]
    assert tts.tone_of({}) is None
    # Korean and multi-syllable keys don't change (their cached audio stays valid).
    assert tts.cache_key("你好", "zh") == tts.cache_key("你好", "zh", None)
    assert tts.cache_key("马", "zh", 3) != tts.cache_key("马", "zh")
    # pack looks audio up with the same key tts wrote it under.
    item = {"id": "zh.w.ma3", "text": "马", "tones": "ma3"}
    assert tts.item_key(item, "zh", {}) == tts.cache_key("马", "zh", 3)

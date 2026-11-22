import json
import re
import zipfile
from pathlib import Path

import pytest
import yaml

from pipeline import fetch
from pipeline.build import build
from pipeline.group import parse_plan
from pipeline.importers.krdict import load_beginner, short_gloss, vocabulary_candidates
from pipeline.pack import pack, write_attribution
from pipeline.validate import validate_course_dir

FIXTURE = Path(__file__).parent / "fixtures" / "krdict-mini.json"


@pytest.fixture
def dump(tmp_path) -> Path:
    path = tmp_path / "krdict.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.write(FIXTURE, "1_15_20261119.json")
    return path


@pytest.fixture
def courses(tmp_path) -> Path:
    course = tmp_path / "courses" / "ko-en"
    course.mkdir(parents=True)
    meta = {
        "id": "ko-en",
        "target": "ko",
        "glosses": ["en", "id"],
        "levels": ["topik1", "topik2"],
        "version": "0.0.1",
        "units": [],
    }
    (course / "course.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    return tmp_path / "courses"


def fake_senses(prompt: str, picks: dict[str, int]) -> str:
    """Reply to a pick-senses prompt: `picks`, else the first offered sense of each word."""
    offered = re.findall(r"^  (ko\.w\.[a-z0-9-]+) \| .*? \| (\d+):", prompt, re.M)
    return json.dumps({"senses": {i: picks.get(i, int(n)) for i, n in offered}})


def fake_claude(units, senses=None):
    """A stand-in for `claude -p`: returns `units` (lists of IDs) as a plan, records prompts."""

    def run(prompt: str) -> str:
        if "dictionary senses" in prompt:
            run.sense_prompts.append(prompt)
            return fake_senses(prompt, senses or {})
        run.prompts.append(prompt)
        plan = [
            {"slug": f"theme-{n}", "title_en": f"Theme {n}", "title_id": f"Tema {n}", "items": ids}
            for n, ids in enumerate(units)
        ]
        return "Here you go:\n" + json.dumps({"units": plan})

    run.prompts, run.sense_prompts = [], []
    return run


def entries(dump):
    beginner, total = load_beginner(dump)
    return {e.target_code: e for e in beginner}, total


def test_parser(dump):
    by_code, total = entries(dump)
    assert total == 15
    eye = by_code[72704]
    assert (eye.word, eye.pos, eye.homonym, eye.pronunciation) == ("눈", "명사", 1, "눈")
    assert [(s.number, s.en, s.id) for s in eye.senses] == [
        (1, "eye", "mata"),
        (2, "eyesight", None),
    ]
    assert eye.source_ref == "krdict:72704#1"
    assert by_code[58272].senses[0].en == "eat, have"
    assert by_code[26799].senses[0].id == "bersama"


def test_short_gloss():
    assert short_gloss("eat; have; consume") == "eat, have"
    assert short_gloss("(no equivalent)") is None
    assert short_gloss("") is None


def test_beginner_filter(dump):
    by_code, _ = entries(dump)
    assert 10008 not in by_code  # 중급
    candidates, stats = vocabulary_candidates(list(by_code.values()))
    words = {e.word for e in candidates}
    assert words == {"눈", "같이", "먹다", "좋다", "하나", "물", "밥", "오다"}
    assert stats["dropped: phrase"] == 1
    assert stats["dropped: no en gloss"] == 1  # 가다: "(no equivalent)"
    assert stats["dropped: 조사"] == stats["dropped: 접사"] == stats["dropped: 보조 동사"] == 1
    assert stats["with id gloss"] == 8  # all but 하나


PLAN = [["ko.w.nun", "ko.w.nun-20198", "ko.w.gachi", "ko.w.meokda", "ko.w.jota"]]


def test_build_writes_valid_units_with_stable_ids(dump, courses, tmp_path):
    run = fake_claude(PLAN, senses={"ko.w.nun": 2})
    summary = build("ko-en", 1, run=run, courses=courses, cache=tmp_path / "cache", source_zip=dump)
    assert summary.new_units == [("units/010-theme-0.yaml", 5)]
    errors, units = validate_course_dir(courses / "ko-en")
    assert errors == []
    items = {i["id"]: i for i in units[0]["items"]}
    assert units[0]["id"] == "ko-010-theme-0"
    assert items["ko.w.nun"]["source_ref"] == "krdict:72704#2"  # sense picked by "Claude"
    assert items["ko.w.nun"]["gloss"] == {"en": "eyesight"}  # sense 2 has no id gloss
    assert run.sense_prompts[0].count("\n  ko.w.") == 1  # only 눈 72704 has several senses
    assert items["ko.w.nun-20198"]["gloss"] == {"en": "snow", "id": "salju"}
    assert items["ko.w.gachi"]["roman"] == "gachi"
    assert all(
        i["review"] == "needs_review" and i["license"] == "CC BY-SA 2.0 KR" for i in items.values()
    )
    assert "ko.w.oda" in run.prompts[0] and "사과" not in run.prompts[0]


def test_build_merges_without_clobbering(dump, courses, tmp_path):
    cache = tmp_path / "cache"
    build("ko-en", 1, run=fake_claude(PLAN), courses=courses, cache=cache, source_zip=dump)
    unit_file = courses / "ko-en" / "units" / "010-theme-0.yaml"
    unit = yaml.safe_load(unit_file.read_text(encoding="utf-8"))
    unit["items"][0]["review"] = "reviewed"
    unit["items"][0]["gloss"]["en"] = "eye (body part)"
    unit_file.write_text(
        yaml.safe_dump(unit, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    edited = unit_file.read_text(encoding="utf-8")

    # Same target: nothing to do, nothing rewritten, no LLM call.
    run = fake_claude([])
    build("ko-en", 1, run=run, courses=courses, cache=cache, source_zip=dump)
    assert run.prompts == []
    assert unit_file.read_text(encoding="utf-8") == edited

    # One more unit: only new words are offered, IDs never reused, the edited unit is untouched.
    run = fake_claude([["ko.w.hana", "ko.w.mul", "ko.w.bap", "ko.w.oda", "ko.w.nun-72704"]])
    with pytest.raises(RuntimeError, match="unknown id ko.w.nun-72704"):
        build("ko-en", 2, run=run, courses=courses, cache=cache, source_zip=dump)
    assert "ko.w.nun |" not in run.prompts[0] and "ko.w.meokda" not in run.prompts[0]
    run = fake_claude([["ko.w.hana", "ko.w.mul", "ko.w.bap", "ko.w.oda", "ko.w.gachi-26799"]])
    with pytest.raises(RuntimeError):
        build("ko-en", 2, run=run, courses=courses, cache=cache, source_zip=dump)
    assert unit_file.read_text(encoding="utf-8") == edited
    assert len(list((courses / "ko-en" / "units").iterdir())) == 1


def test_parse_plan_rejects_bad_output():
    pool = {f"ko.w.w{i}" for i in range(10)}
    good = {
        "slug": "a",
        "title_en": "A",
        "title_id": "A",
        "items": [f"ko.w.w{i}" for i in range(5)],
    }
    assert parse_plan(json.dumps({"units": [good]}), pool, 1)[0].slug == "a"
    bad = [
        ("not json", "no JSON"),
        (json.dumps({"units": [good, good]}), "duplicate"),
        (json.dumps({"units": [{**good, "items": ["ko.w.w1"] * 4}]}), "at least 5"),
        (json.dumps({"units": [{**good, "items": ["ko.w.new", *good["items"][1:]]}]}), "unknown"),
        (json.dumps({"units": [{**good, "items": ["ko.w.w1", *good["items"][1:]]}]}), "twice"),
        (json.dumps({"units": [{**good, "slug": "Bad Slug"}]}), "pattern"),
    ]
    for text, message in bad:
        with pytest.raises(ValueError, match=message):
            parse_plan(text, pool, 1 if message != "duplicate" else 2)


def test_group_retries_once_then_uses_cache(dump, courses, tmp_path):
    replies = iter(
        [
            "nope",
            json.dumps(
                {"units": [{"slug": "a", "title_en": "A", "title_id": "A", "items": PLAN[0]}]}
            ),
        ]
    )
    calls = []

    def run(prompt):
        if "dictionary senses" in prompt:
            return fake_senses(prompt, {})
        calls.append(prompt)
        return next(replies)

    cache = tmp_path / "cache"
    build("ko-en", 1, dry_run=True, run=run, courses=courses, cache=cache, source_zip=dump)
    assert len(calls) == 2
    build("ko-en", 1, dry_run=True, run=run, courses=courses, cache=cache, source_zip=dump)
    assert len(calls) == 2  # served from cache/llm
    assert not (courses / "ko-en" / "units").exists()  # dry run writes nothing


def test_pack_is_valid(dump, courses, tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1795000000")
    build("ko-en", 1, run=fake_claude(PLAN), courses=courses, cache=tmp_path / "c", source_zip=dump)
    out = pack("ko-en", courses=courses, dist=tmp_path / "dist")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    course = json.loads((out / "course.json").read_text(encoding="utf-8"))
    assert len(course["units"][0]["items"]) == 5
    assert manifest["attribution"] == [
        {
            "source": "krdict",
            "license": "CC BY-SA 2.0 KR",
            "items": 5,
            "url": "https://krdict.korean.go.kr",
            "authors": ["국립국어원 (National Institute of Korean Language)"],
        }
    ]
    attribution = tmp_path / "ATTRIBUTION.md"
    write_attribution(courses, attribution)
    assert (
        "[한국어기초사전 (Basic Korean Dictionary)](https://krdict.korean.go.kr)"
        in attribution.read_text()
    )


def test_sources_lock_check(tmp_path, dump):
    sources, lock = tmp_path / "sources", tmp_path / "sources.lock"
    fetch.fetch_krdict(dump, sources, lock)
    assert fetch.check("krdict", sources, lock) == sources / "krdict" / "krdict-json.zip"
    (sources / "krdict" / "krdict-json.zip").write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="sha256"):
        fetch.check("krdict", sources, lock)


def test_krdict_json_seq():
    html = """<button onclick="batchDownload('221')"><i></i> 엑셀 전체 내려받기</button>
    <button onclick="batchDownload('223')" style="x"><i></i> Json 전체 내려받기</button>"""
    assert fetch.krdict_json_seq(html) == "223"


def test_core_words_come_first_and_must_be_unambiguous(dump, courses, tmp_path):
    core = courses / "ko-en" / "core-words.yaml"
    core.write_text("words: [눈]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="'눈' matches 2 candidates: 72704"):
        build("ko-en", 1, run=fake_claude(PLAN), courses=courses, cache=tmp_path, source_zip=dump)
    core.write_text("words: [하나, 눈#20198]\n", encoding="utf-8")
    run = fake_claude([])
    with pytest.raises(RuntimeError):  # the empty plan is invalid; we only want the prompt
        build("ko-en", 1, run=run, courses=courses, cache=tmp_path, source_zip=dump)
    rows = [line for line in run.prompts[0].splitlines() if line.startswith("ko.w.")]
    assert [r.split(" | ")[1] for r in rows[:2]] == ["하나", "눈"]
    assert rows[1].startswith("ko.w.nun |")  # core words get the plain ID first


def test_parse_senses_rejects_bad_picks():
    from pipeline.group import parse_senses

    choices = {"ko.w.a": {1, 2}, "ko.w.b": {1, 3}}
    assert parse_senses('{"senses": {"ko.w.a": 2, "ko.w.b": 3}}', choices) == {
        "ko.w.a": 2,
        "ko.w.b": 3,
    }
    for text, message in [
        ('{"senses": {"ko.w.a": 2}}', "missing"),
        ('{"senses": {"ko.w.a": 2, "ko.w.b": 2}}', "not offered"),
        ('{"senses": {"ko.w.a": 1, "ko.w.b": 1, "ko.w.c": 1}}', "extra"),
    ]:
        with pytest.raises(ValueError, match=message):
            parse_senses(text, choices)

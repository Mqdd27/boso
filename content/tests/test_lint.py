import json
import zipfile
from pathlib import Path

import pytest
import yaml

from pipeline.importers.krdict import load_beginner
from pipeline.lint import gloss_problems, lint

FIXTURE = Path(__file__).parent / "fixtures" / "krdict-mini.json"


def item(id_, text, en, idn, ref):
    gloss = {"en": en} | ({"id": idn} if idn is not None else {})
    return {
        "id": id_,
        "type": "word",
        "text": text,
        "roman": id_.split(".")[-1],
        "gloss": gloss,
        "source": "krdict",
        "license": "CC BY-SA 2.0 KR",
        "source_ref": ref,
        "review": "needs_review",
    }


@pytest.fixture
def course(tmp_path) -> Path:
    course = tmp_path / "ko-en"
    (course / "units").mkdir(parents=True)
    unit = {
        "id": "ko-010-test",
        "title": {"en": "Test"},
        "level": "topik1",
        "items": [
            item("ko.w.nun", "눈", "eyesight", None, "krdict:72704#2"),  # no id gloss
            item("ko.w.mul", "물", "water", "puluh ribu", "krdict:10001#1"),  # bad number
            item("ko.w.bap", "밥", "water", "nasi", "krdict:10002#1"),  # same en as 물
            item("ko.w.gachi", "같이", "ma&apos, am", "bersama", "krdict:26799#1"),
        ],
    }
    (course / "units" / "010-test.yaml").write_text(json.dumps(unit), encoding="utf-8")
    meta = {
        "id": "ko-en",
        "target": "ko",
        "glosses": ["en", "id"],
        "levels": ["topik1"],
        "version": "0.0.1",
        "units": ["units/010-test.yaml"],
    }
    (course / "course.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    (course / "core-words.yaml").write_text("words: [물, 하나, 눈#20198]\n", encoding="utf-8")
    return course


@pytest.fixture
def entries(tmp_path):
    path = tmp_path / "krdict.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.write(FIXTURE, "1_15_20261119.json")
    return load_beginner(path)[0]


def test_gloss_problems():
    assert gloss_problems("id", "puluh ribu") != []
    assert gloss_problems("id", "sepuluh ribu, puluh") == []
    assert gloss_problems("id", "kakak atau") != []
    assert gloss_problems("en", "father (of") != []
    assert gloss_problems("en", "ma&apos, am") != []
    assert gloss_problems("id", "") == ["id gloss is empty"]
    assert gloss_problems("en", "eat, have") == []


def test_lint_reports_with_krdict_suggestions(course, entries):
    findings = {
        (f.item, f.problem.split(" ")[0] + " " + f.problem.split(" ")[1]): f
        for f in lint(course, entries)
    }
    assert findings["ko.w.nun", "id gloss"].suggestion.startswith("krdict:72704#1: en 'eye'")
    assert "bare multiplier" in findings["ko.w.mul", "id gloss"].problem
    assert findings["ko.w.bap", "same en"].problem == "same en gloss 'water' as ko.w.mul"
    assert "HTML entity" in findings["ko.w.gachi", "en gloss"].problem
    core = sorted(f.problem for f in lint(course, entries) if f.unit == "-")
    assert core == [
        "core word '눈#20198' is not in any unit",
        "core word '하나' is not in any unit",
    ]


def test_lint_without_dump_and_never_edits(course):
    before = {p: p.read_bytes() for p in course.rglob("*.yaml")}
    findings = lint(course, [])
    assert findings and all(f.suggestion == "" for f in findings)
    assert {p: p.read_bytes() for p in course.rglob("*.yaml")} == before

import copy
import json

import pytest

from pipeline.cli import main
from pipeline.validate import ROOT, validate_all, validate_course_dir, validate_pack_file

EXAMPLES = ROOT / "schema" / "examples"
KO = json.loads((EXAMPLES / "ko-en.course.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((EXAMPLES / "ko-en.manifest.json").read_text(encoding="utf-8"))


def test_repo_validates():
    errors, stats = validate_all()
    assert errors == []
    assert stats["courses"] == 2
    assert stats["examples"] == 3


def test_cli_exit_codes(tmp_path):
    assert main(["validate"]) == 0
    (tmp_path / "schema" / "examples").mkdir(parents=True)
    (tmp_path / "schema" / "examples" / "bad.course.json").write_text("{}")
    assert main(["validate", "--root", str(tmp_path)]) == 1


def item(course):
    return course["units"][0]["items"][0]


def tones_on_korean(c):
    item(c)["tones"] = "an1"


def word_with_sentence_id(c):
    item(c)["id"] = "ko.s.annyeonghaseyo"


def duplicate_id(c):
    c["units"][0]["items"][1]["id"] = item(c)["id"]


def chinese_id_in_korean_course(c):
    item(c)["id"] = "zh.w.annyeonghaseyo"


INVALID_COURSES = {
    "bad id pattern": lambda c: item(c).update(id="ko.w.Annyeong"),
    "missing gloss.en": lambda c: item(c).update(gloss={"id": "Halo"}),
    "missing license": lambda c: item(c).pop("license"),
    "bad review value": lambda c: item(c).update(review="ok"),
    "unknown field": lambda c: item(c).update(extra=1),
    "tones on korean": tones_on_korean,
    "type/id mismatch": word_with_sentence_id,
    "glosses without en": lambda c: c.update(glosses=["id"]),
    "bad version": lambda c: c.update(version="1"),
    "no units": lambda c: c.update(units=[]),
    "level not in course": lambda c: c["units"][0].update(level="topik9"),
    "duplicate id": duplicate_id,
    "id of other target": chinese_id_in_korean_course,
}


@pytest.mark.parametrize("mutate", INVALID_COURSES.values(), ids=INVALID_COURSES.keys())
def test_invalid_course_fails(tmp_path, mutate):
    course = copy.deepcopy(KO)
    mutate(course)
    path = tmp_path / "x.course.json"
    path.write_text(json.dumps(course), encoding="utf-8")
    assert validate_pack_file(path)


INVALID_MANIFESTS = {
    "no attribution": lambda m: m.update(attribution=[]),
    "bad build_date": lambda m: m.update(build_date="yesterday"),
    "units in course meta": lambda m: m["course"].update(units=[]),
    "wrong schema_version": lambda m: m.update(schema_version=2),
}


@pytest.mark.parametrize("mutate", INVALID_MANIFESTS.values(), ids=INVALID_MANIFESTS.keys())
def test_invalid_manifest_fails(tmp_path, mutate):
    manifest = copy.deepcopy(MANIFEST)
    mutate(manifest)
    path = tmp_path / "x.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_pack_file(path)


def test_course_dir_with_units(tmp_path):
    course_dir = tmp_path / "ko-en"
    (course_dir / "units").mkdir(parents=True)
    unit = copy.deepcopy(KO["units"][0])
    (course_dir / "units" / "010-greetings.yaml").write_text(json.dumps(unit), encoding="utf-8")
    meta = {k: v for k, v in KO.items() if k != "units"}
    meta["units"] = ["units/010-greetings.yaml"]
    (course_dir / "course.yaml").write_text(json.dumps(meta), encoding="utf-8")

    errors, units = validate_course_dir(course_dir)
    assert errors == []
    assert len(units) == 1

    (course_dir / "units" / "011-orphan.yaml").write_text(json.dumps(unit), encoding="utf-8")
    errors, _ = validate_course_dir(course_dir)
    assert any("not listed" in e for e in errors)

    (course_dir / "units" / "010-greetings.yaml").unlink()
    errors, _ = validate_course_dir(course_dir)
    assert any("not found" in e for e in errors)

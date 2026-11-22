import shutil
from pathlib import Path

import pytest
import yaml

from pipeline import hangul
from pipeline.nlp.ko import compose, decompose
from pipeline.validate import check, validate_course_dir

KO_EN = Path(__file__).resolve().parents[1] / "courses" / "ko-en"
SPEC = yaml.safe_load((KO_EN / "hangul.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("parts", "syllable"),
    [(("ㄱ", "ㅏ", ""), "가"), (("ㄱ", "ㅏ", "ㄱ"), "각"), (("ㄲ", "ㅙ", ""), "꽤"),
     (("ㅇ", "ㅣ", "ㄺ"), "읽"), (("ㅎ", "ㅣ", "ㅎ"), "힣")],
)  # fmt: skip
def test_compose_and_decompose(parts, syllable):
    assert compose(*parts) == syllable
    assert decompose(syllable) == parts


def test_decompose_rejects_non_syllables():
    assert decompose("ㄱ") is None and decompose("a") is None


def test_units_follow_the_curriculum():
    units = dict(hangul.units(SPEC))
    texts = {rel: [i["text"] for i in u["items"]] for rel, u in units.items()}
    assert list(units) == [
        f"units/{n:03d}-{u['slug']}.yaml" for n, u in enumerate(SPEC["units"], 1)
    ]
    assert texts["units/001-basic-vowels.yaml"] == list("ㅏㅓㅗㅜㅡㅣ")
    assert texts["units/002-basic-consonants-1.yaml"] == list("ㄱㄴㄷㄹㅁ")
    assert texts["units/003-basic-consonants-2.yaml"] == list("ㅂㅅㅇㅈㅎ")
    assert texts["units/007-tense-consonants.yaml"][:5] == list("ㄲㄸㅃㅆㅉ")
    assert len(texts["units/008-combined-vowels.yaml"]) == 9 + 3
    assert all(
        decompose(t)[2] for t in texts["units/009-final-consonants.yaml"]
    )  # all have batchim
    for unit in units.values():
        assert unit["kind"] == "script"
        for item in unit["items"]:
            assert item["type"] == "char" and item["id"].startswith("ko.c.")
            assert item["source"] == "boso" and item["review"] == "needs_review"
            assert check(item, "item", item["id"]) == []


def test_items_explain_sounds():
    items = {i["text"]: i for _, u in hangul.units(SPEC) for i in u["items"]}
    assert items["ㄱ"]["roman"] == "g/k" and items["ㅓ"]["roman"] == "eo"
    assert items["가"]["roman"] == "ga" and items["가"]["gloss"]["en"] == "syllable ga: ㄱ + ㅏ"
    assert items["옷"]["gloss"]["en"] == "syllable ot: ㅇ + ㅗ + final ㅅ, read t"
    assert items["꽃"]["gloss"]["id"] == "suku kata kkot: ㄲ + ㅗ + akhir ㅊ, dibaca t"


def test_sounds_are_unique_within_letters_and_within_syllables():
    # A vowel and its ㅇ-syllable share a sound (ㅑ / 야 = ya); the app never offers both at once.
    items = [i for _, u in hangul.units(SPEC) for i in u["items"]]
    for kind in (True, False):
        romans = [i["roman"] for i in items if (decompose(i["text"]) is None) == kind]
        assert len(romans) == len(set(romans))
    assert len({i["id"] for i in items}) == len(items)


def test_readings():
    assert hangul.reading("ㄱ") == "가" and hangul.reading("ㅏ") == "아"
    assert hangul.reading("ㅢ") == "의" and hangul.reading("ㄲ") == "까"


@pytest.fixture
def course(tmp_path) -> Path:
    course = tmp_path / "ko-en"
    (course / "units").mkdir(parents=True)
    shutil.copy(KO_EN / "hangul.yaml", course)
    shutil.copy(KO_EN / "units" / "010-greetings-and-manners.yaml", course / "units")
    meta = yaml.safe_load((KO_EN / "course.yaml").read_text(encoding="utf-8"))
    meta["units"] = ["units/010-greetings-and-manners.yaml"]
    (course / "course.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True), encoding="utf-8")
    return course


def test_generate_is_deterministic_and_never_clobbers(course):
    first = hangul.generate(course)
    assert len(first.written) == 9 and first.readings == 40
    order = yaml.safe_load((course / "course.yaml").read_text(encoding="utf-8"))["units"]
    assert order[:9] == [rel for rel, _ in hangul.units(SPEC)]
    assert order[9:] == ["units/010-greetings-and-manners.yaml"]
    errors, units = validate_course_dir(course)
    assert errors == [] and len(units) == 10

    edited = course / "units" / "001-basic-vowels.yaml"
    edited.write_text(edited.read_text(encoding="utf-8").replace("vowel a", "vowel a!"))
    (course / "readings.yaml").write_text("ko.c.a: 아아\n", encoding="utf-8")
    again = hangul.generate(course)
    assert again.written == [] and again.kept == ["units/001-basic-vowels.yaml"]
    assert len(again.unchanged) == 8 and again.readings == 39
    assert "vowel a!" in edited.read_text(encoding="utf-8")
    readings = yaml.safe_load((course / "readings.yaml").read_text(encoding="utf-8"))
    assert readings["ko.c.a"] == "아아" and readings["ko.c.giyeok"] == "가"


def test_old_packs_without_kind_or_char_stay_valid():
    unit = {"id": "ko-010-x", "title": {"en": "X"}, "level": "topik1", "items": [
        {"id": "ko.w.ne", "type": "word", "text": "네", "roman": "ne", "gloss": {"en": "yes"},
         "source": "krdict", "license": "CC BY-SA 2.0 KR", "review": "needs_review"}]}  # fmt: skip
    assert check(unit, "unit", "u") == []
    assert check({**unit, "kind": "lesson"}, "unit", "u") != []
    char = {**unit["items"][0], "type": "char"}  # a char needs a ko.c. id
    assert check(char, "item", "i") != []

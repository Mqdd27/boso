import gzip
import json
import re

import pytest
import yaml

from pipeline.build_zh import build, parse_glosses
from pipeline.importers import cedict
from pipeline.nlp.zh import mark, roman, slug, tones
from pipeline.validate import validate_course_dir

CEDICT = """\
# CC-CEDICT test fixture
你好 你好 [ni3 hao3] /hello; hi/
你 你 [ni3] /you (informal)/
謝謝 谢谢 [xie4 xie5] /to thank/thanks/
他 他 [ta1] /he or him/(used for either sex when the sex is unknown or unimportant)/
她 她 [ta1] /she/
它 它 [ta1] /it/
的 的 [de5] /of; ~'s (possessive particle)/
的 的 [di4] /(bound form) bull's-eye; target/
和 和 [He2] /surname He/
和 和 [he2] /(joining two nouns) and; together with; with/
女兒 女儿 [nu:3 er2] /daughter/
一點 一点 [yi1 dian3] /a bit; a little bit/
一點兒 一点儿 [yi1 dian3 r5] /erhua variant of 一點|一点[yi1 dian3]/
"""
HSK1 = "\ufeff你好\r\n你\r\n谢谢\r\n他\r\n她\r\n它\r\n的\r\n和\r\n女儿\r\n一点儿\r\n没有词\r\n"


@pytest.mark.parametrize(
    ("pinyin", "marked", "numbered", "id_slug"),
    [
        ("da3 dian4 hua4", "dǎdiànhuà", "da3 dian4 hua4", "da3dian4hua4"),
        ("nu:3 er2", "nǚ'ér", "nü3 er2", "nv3er2"),
        ("Xi1 an1", "Xī'ān", "xi1 an1", "xi1an1"),
        ("xie4 xie5", "xièxie", "xie4 xie5", "xie4xie5"),
        ("yi1 dian3 r5", "yīdiǎnr", "yi1 dian3 r5", "yi1dian3r5"),
        ("zou3", "zǒu", "zou3", "zou3"),
        ("gui4", "guì", "gui4", "gui4"),
    ],
)
def test_pinyin(pinyin, marked, numbered, id_slug):
    assert roman(pinyin) == marked
    assert tones(pinyin) == numbered
    assert slug(pinyin) == id_slug


def test_mark_puts_the_tone_on_the_right_vowel():
    assert [mark(s) for s in ["hao3", "dou1", "liu4", "lüe4", "er2", "m2"]] == [
        "hǎo",
        "dōu",
        "liù",
        "lüè",
        "ér",
        "m",
    ]


def test_cedict_skips_cross_references():
    entries = cedict.parse(CEDICT.splitlines())
    he = [e for e in entries if e.simp == "和"]
    assert [d for _, d in cedict.senses(he)] == ["(joining two nouns) and; together with; with"]


@pytest.fixture
def sources(tmp_path):
    path = tmp_path / "cedict.txt.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(CEDICT)
    hsk = tmp_path / "hsk1.txt"
    hsk.write_text(HSK1, encoding="utf-8")
    return path, {1: hsk, 2: hsk}


@pytest.fixture
def courses(tmp_path):
    course = tmp_path / "courses" / "zh-en"
    course.mkdir(parents=True)
    meta = {
        "id": "zh-en",
        "target": "zh",
        "glosses": ["en", "id"],
        "levels": ["hsk1", "hsk2"],
        "version": "0.0.1",
        "units": [],
    }
    (course / "course.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    return tmp_path / "courses"


def fake_claude(prompt: str) -> str:
    """Two units in pool order; the last offered sense of each word; glosses "id: <English>"."""
    if '"glosses"' in prompt:
        rows = re.findall(r"^(zh\.w\.\S+) \| \S+ \| \S+ \| (.+)$", prompt, re.M)
        return json.dumps({"glosses": {i: f"id: {en}"[:80] for i, en in rows}})
    if '"senses"' in prompt:
        picks: dict[str, int] = {}
        for i, options in re.findall(r"^  (zh\.w\.\S+) \| \S+ \| (.+)$", prompt, re.M):
            picks[i] = int(re.findall(r"(?:^|; )(\d+): ", options)[-1])
        return json.dumps({"senses": picks})
    ids = re.findall(r"^(zh\.w\.\S+) \|", prompt, re.M)
    half = len(ids) // 2
    units = [ids[:half], ids[half:]]
    return json.dumps(
        {
            "units": [
                {"slug": f"t-{n}", "title_en": f"T {n}", "title_id": f"T {n}", "items": u}
                for n, u in enumerate(units)
            ]
        }
    )


def test_build_writes_valid_hsk_units(sources, courses, tmp_path):
    summary = build(
        level=1, courses=courses, run=fake_claude, cache=tmp_path / "cache", sources=sources
    )
    assert summary.stats["not in CC-CEDICT"] == 1  # 没有词
    assert [rel for rel, _ in summary.new_units] == ["units/010-t-0.yaml", "units/011-t-1.yaml"]
    errors, units = validate_course_dir(courses / "zh-en")
    assert errors == []
    items = {i["text"]: i for u in units for i in u["items"]}
    assert len(items) == 10
    # 他/她/它 are all ta1: the first keeps the plain ID.
    assert [items[w]["id"] for w in "他她它"] == ["zh.w.ta1", "zh.w.ta1-5979", "zh.w.ta1-5b83"]
    assert (items["女儿"]["roman"], items["女儿"]["tones"]) == ("nǚ'ér", "nü3 er2")
    # Erhua borrows 一点's senses, keeps its own pinyin.
    assert items["一点儿"]["gloss"]["en"] == "a bit; a little bit"
    assert items["一点儿"]["tones"] == "yi1 dian3 r5"
    # The picked sense (the fake picks the last one): 的 is di4 here.
    assert items["的"]["tones"] == "di4"
    assert items["谢谢"]["gloss"] == {"en": "thanks", "id": "id: thanks"}
    assert items["谢谢"]["gloss_sources"] == {"id": {"source": "boso", "license": "CC BY-SA 4.0"}}
    assert {i["source"] for i in items.values()} == {"cc-cedict"}
    assert {u["level"] for u in units} == {"hsk1"}

    # A second run finds nothing new and writes nothing.
    files = {p: p.read_bytes() for p in (courses / "zh-en").rglob("*.yaml")}
    again = build(
        level=1, courses=courses, run=fake_claude, cache=tmp_path / "cache", sources=sources
    )
    assert again.new_units == [] and again.stats["already in a unit"] == 10
    assert files == {p: p.read_bytes() for p in (courses / "zh-en").rglob("*.yaml")}


def test_parse_glosses_rejects_missing_and_long():
    ids = {"zh.w.a", "zh.w.b"}
    assert parse_glosses('{"glosses": {"zh.w.a": "x", "zh.w.b": " y "}}', ids)["zh.w.b"] == "y"
    with pytest.raises(ValueError, match="missing"):
        parse_glosses('{"glosses": {"zh.w.a": "x"}}', ids)
    with pytest.raises(ValueError, match="80"):
        parse_glosses(json.dumps({"glosses": {"zh.w.a": "x" * 81, "zh.w.b": "y"}}), ids)


def test_pinyin_units_from_the_real_pinyin_yaml(courses):
    import shutil
    from pathlib import Path

    from pipeline.pinyin import generate

    course_dir = courses / "zh-en"
    shutil.copy(Path(__file__).parents[1] / "courses/zh-en/pinyin.yaml", course_dir)
    summary = generate(course_dir)
    assert len(summary.written) == 9 and summary.readings == 58
    errors, units = validate_course_dir(course_dir)
    assert errors == []
    assert all(u["kind"] == "script" for u in units)
    tones_unit = units[0]["items"]
    assert [i["text"] for i in tones_unit] == ["mā", "má", "mǎ", "mà", "ma"]
    assert [i["tones"] for i in tones_unit] == ["ma1", "ma2", "ma3", "ma4", "ma5"]
    readings = yaml.safe_load((course_dir / "readings.yaml").read_text(encoding="utf-8"))
    assert readings["zh.c.ma3"] == "马"
    assert generate(course_dir).unchanged == [rel for rel in summary.written]  # idempotent


@pytest.mark.parametrize(
    ("definition", "gloss"),
    [
        (
            "you (informal, as opposed to courteous 您[nin2])",
            "you (informal, as opposed to courteous 您)",
        ),
        ("dish (of food) (CL:樣|样[yang4],道[dao4],盤|盘[pan2])", "dish (of food)"),
        ("(specifier) that; the; those (colloquial pr. [nei4])", "(specifier) that; the; those"),
        (
            "(after a numeral) number (e.g. 237號房間|237号房间[er4 san1 qi1 hao4 fang2 jian1])",
            "(after a numeral) number (e.g. 237号房间)",
        ),
        ("to be (located) at", "to be (located) at"),
    ],
)
def test_clean_definition(definition, gloss):
    assert cedict.clean(definition) == gloss

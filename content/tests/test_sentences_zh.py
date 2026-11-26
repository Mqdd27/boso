from pipeline import sentences_zh as z
from pipeline.importers import cedict
from pipeline.sentences import Candidate


def unit(*words):
    return {"items": [{"id": f"zh.w.{w}", "type": "word", "text": w} for w in words]}


def cand(n, text, en="x"):
    return Candidate(
        id=f"zh.s.t{n}",
        text=text,
        source="tatoeba",
        license="CC BY 2.0 FR",
        source_ref=f"tatoeba:{n}",
        author="a",
        en={"text": en, "author": "b", "license": "CC BY 2.0 FR", "ref": "tatoeba:9"},
    )


ENTRIES = cedict.parse(["說 说 [shuo1] /to speak/", "我 我 [wo3] /I; me/"])
UNITS = [unit("我", "你", "是", "好"), unit("女儿", "她", "的")]


def test_place_in_the_earliest_unit_with_one_new_word_at_most():
    cands = [
        cand(1, "我是你。"),  # unit 0
        cand(2, "她是我女儿。"),  # unit 1
        cand(3, "你好吗？"),  # 吗 new in unit 0, but 1 of 3 characters: too few known
        cand(4, "我說你好。"),  # traditional 說
        cand(5, "我是ABC。"),  # Latin
        cand(6, "你好。"),  # two words
    ]
    placed = {p.candidate.id: p for p in z.place(cands, UNITS, z.traditional_only(ENTRIES))}
    assert set(placed) == {"zh.s.t1", "zh.s.t2"}
    assert (placed["zh.s.t1"].unit, placed["zh.s.t2"].unit) == (0, 1)
    assert placed["zh.s.t2"].own


def test_roman_has_one_word_per_card():
    taught = {"女儿": "nǚ'ér", "她": "tā"}
    text = "她是我女儿。"
    assert z.roman(text, taught) == "Tā shì wǒ nǚ'ér."
    assert z.words(text) == ["她", "是", "我", "女儿"]


def test_select_skips_same_meaning():
    placed = z.place([cand(1, "我是你。", "Same"), cand(2, "你是我。", "Same")], UNITS, set())
    chosen = z.select(placed, 6, UNITS)
    assert [p.candidate.id for p in chosen[0]] == ["zh.s.t1"]

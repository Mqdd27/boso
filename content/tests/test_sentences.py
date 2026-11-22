import bz2
import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml

from pipeline import pack, sentences
from pipeline.importers import krdict, tatoeba
from pipeline.validate import check, validate_course_dir


def _tsv(path: Path, rows: list[list]) -> Path:
    path.write_bytes(bz2.compress("".join("\t".join(map(str, r)) + "\n" for r in rows).encode()))
    return path


@pytest.fixture
def tatoeba_files(tmp_path) -> dict[str, Path]:
    d = "2020-01-01 00:00:00"
    files = {
        "kor_sentences_detailed": [
            [1, "kor", "밥 먹었어요?", "minsu", d, d],
            [2, "kor", "물 주세요.", r"\N", d, d],  # orphan: no author
            [3, "kor", "가고 싶어.", "jiwoo", d, d],  # tagged @change
            [4, "kor", "물 마셔요.", "jiwoo", d, d],  # CC0
        ],
        "kor-eng_links": [[1, 11], [1, 10], [4, 12], [4, 13]],
        "kor-ind_links": [[1, 20]],
        "kor_tags": [[3, "@change"], [1, "food"]],
        "eng_sentences_detailed": [
            [10, "eng", "Did you eat?", "anna", d, d],
            [11, "eng", "Have you eaten?", "bob", d, d],
            [12, "eng", "Drink water.", "carl", d, d],
            [13, "eng", "I drink water.", "dana", d, d],
        ],
        "eng_tags": [[12, "@needs native check"]],
        "ind_sentences_detailed": [[20, "ind", "Sudah makan?", "budi", d, d]],
        "ind_tags": [],
    }
    out = {name: _tsv(tmp_path / f"{name}.tsv.bz2", rows) for name, rows in files.items()}
    cc0 = b"4\tkor\t\xeb\xac\xbc\n13\teng\tI drink water.\n"
    with tarfile.open(tmp_path / "sentences_CC0.tar.bz2", "w:bz2") as tar:
        info = tarfile.TarInfo("sentences_CC0.csv")
        info.size = len(cc0)
        tar.addfile(info, io.BytesIO(cc0))
    out["sentences_CC0"] = tmp_path / "sentences_CC0.tar.bz2"
    return out


def test_tatoeba_keeps_only_attributable_clean_sentences(tatoeba_files):
    pairs, stats = tatoeba.load(tatoeba_files)
    assert [p.kor.id for p in pairs] == [1, 4]
    assert stats["dropped: no author"] == 1 and stats["dropped: tag"] == 1
    first, cc0 = pairs
    assert first.kor.author == "minsu" and first.kor.license == tatoeba.CC_BY
    assert first.eng.id == 10 and first.eng.author == "anna"  # oldest translation
    assert first.ind.text == "Sudah makan?" and first.ind.author == "budi"
    assert cc0.kor.license == tatoeba.CC0
    assert cc0.eng.id == 13 and cc0.eng.license == tatoeba.CC0  # 12 is tagged
    assert cc0.ind is None


def test_tags():
    assert tatoeba.bad_tag("@change") and tatoeba.bad_tag("@needs native check")
    assert tatoeba.bad_tag("non-sentence") and not tatoeba.bad_tag("food")


def test_analyze_uses_dictionary_forms_and_word_classes():
    a = sentences.analyze("어제 친구랑 밥을 먹었어요.")
    assert [(lem, cls) for lem, cls, _ in a.lemmas] == [
        ("어제", "A"), ("친구", "N"), ("밥", "N"), ("먹다", "V")
    ]  # fmt: skip
    assert [w for *_, w in a.lemmas] == [0, 1, 2, 3]
    assert a.total == 8  # particles and endings count, the full stop doesn't
    assert ("일", "D") in {(lem, c) for lem, c, _ in sentences.analyze("일 년").lemmas}
    assert ("일", "N") in {(lem, c) for lem, c, _ in sentences.analyze("나 일해").lemmas}
    assert sentences.analyze("1887년에 왔다").foreign
    assert "더" in sentences.analyze("십에 십을 더하면 이십이다.").derived


def test_tokens_drop_surrounding_punctuation():
    assert sentences.tokens("아들이야, 딸이야?") == ["아들이야", "딸이야"]
    assert sentences.tokens("“네!” 하고 말했어요.") == ["네", "하고", "말했어요"]


def _word(item_id, text):
    return {"id": item_id, "type": "word", "text": text}


UNITS = [
    {"items": [_word("ko.w.bap", "밥"), _word("ko.w.il", "일")]},  # 일 as the number one
    {"items": [_word("ko.w.meokda", "먹다"), _word("ko.w.mul", "물")]},
    {"items": [_word("ko.w.ilhada", "일하다"), _word("ko.w.masida", "마시다")]},
]
POS = {"ko.w.il": "수사", "ko.w.bap": "명사", "ko.w.meokda": "동사", "ko.w.mul": "명사"}


def _cand(cid, text, en="x"):
    return sentences.Candidate(
        id=cid, text=text, source="tatoeba", license=tatoeba.CC_BY, source_ref=f"tatoeba:{cid}",
        author="a", en={"text": en, "author": "b", "license": tatoeba.CC_BY, "ref": "tatoeba:9"},
    )  # fmt: skip


def test_known_words_keep_homographs_apart():
    known = sentences.known_words(UNITS[0]["items"], POS)
    assert ("일", "D") in known and ("일", "N") not in known
    assert ("일", "N") in sentences.known_words(UNITS[2]["items"], {})  # 일하다 → 일


def test_place_in_the_earliest_unit_that_fits():
    cands = [
        _cand("a", "밥 먹었어요?"),  # needs 먹다: unit 2
        _cand("b", "물을 마셔요."),  # 물 unit 2, 마시다 unit 3
        _cand("c", "나는 일해요."),  # 일 (work) comes with 일하다 in unit 3; 나 is never taught
        _cand("d", "밥."),  # one word: too short
        _cand("e", "밥 밥 밥 밥 밥 밥 밥 밥 밥."),  # too long
    ]
    placed = {p.candidate.id: p for p in sentences.place(cands, UNITS, 1, 0.8, pos=POS)}
    # 밥 먹었어요 is 4 morphemes: one unknown is 75% known, below 0.8, so it waits for 먹다.
    assert placed["a"].unit == 1 and placed["a"].unknown == [] and placed["a"].own
    assert placed["b"].unit == 2 and placed["b"].unknown == []
    assert placed["c"].unit == 2 and placed["c"].unknown == [("나", "N")]
    assert set(placed) == {"a", "b", "c"}
    strict = {p.candidate.id: p.unit for p in sentences.place(cands, UNITS, 0, 0.9, pos=POS)}
    assert strict == {"a": 1, "b": 2}
    loose = {p.candidate.id: p for p in sentences.place(cands, UNITS, 1, 0.5, pos=POS)}
    assert loose["a"].unit == 0 and loose["a"].unknown == [("먹다", "V")]


def test_select_is_deterministic_and_skips_near_duplicates():
    cands = [
        _cand("t1", "밥 먹었어?", "Have you eaten?"),
        _cand("t2", "밥 먹었어요?", "Have you eaten (polite)?"),  # same content words as t1
        _cand("t3", "물 먹어요.", "Have some water."),
        _cand("t4", "밥 물 먹어요.", "Have some water."),  # same English as t3
    ]
    placed = sentences.place(cands, UNITS, 1, 0.8, pos=POS)
    units = [{"items": []} for _ in UNITS]
    first = sentences.select(placed, 6, units)
    assert first == sentences.select(list(reversed(placed)), 6, units)
    assert [p.candidate.id for p in first[1]] == ["t1", "t3"]
    assert [p.candidate.id for p in sentences.select(placed, 1, units)[1]] == ["t1"]
    existing = [{"items": []}, {"items": [{"id": "x", "type": "sentence", "text": "밥 먹었니?",
                "gloss": {"en": "Ate?"}}]}, {"items": []}]  # fmt: skip
    assert [p.candidate.id for p in sentences.select(placed, 6, existing)[1]] == ["t3"]


def test_parse_translations_validates():
    ok = '{"items": {"ko.s.t1": {"en": "Ate?", "id": "Sudah makan?"}}}'
    assert sentences.parse_translations(ok, {"ko.s.t1"})["ko.s.t1"].id == "Sudah makan?"
    for bad in [
        '{"items": {}}',
        '{"items": {"ko.s.t1": {"en": "Ate?"}}}',
        '{"items": {"ko.s.t1": {"en": " ", "id": "x"}}}',
        '{"items": {"ko.s.t1": {"en": "a", "id": "b"}, "ko.s.t2": {"en": "a", "id": "b"}}}',
        "no json",
    ]:
        with pytest.raises(ValueError):
            sentences.parse_translations(bad, {"ko.s.t1"})


def _course(tmp_path) -> Path:
    course = tmp_path / "ko-en"
    (course / "units").mkdir(parents=True)
    meta = {"id": "ko-en", "target": "ko", "glosses": ["en", "id"], "levels": ["topik1"],
            "version": "0.2.0", "units": []}  # fmt: skip
    words = [("밥", "bap", "rice", "20279"), ("먹다", "meokda", "eat", "34869"),
             ("물", "mul", "water", "29602")]  # fmt: skip
    for n, (text, roman, en, code) in enumerate(words, 10):
        rel = f"units/{n:03d}-u.yaml"
        item = {"id": f"ko.w.{roman}", "type": "word", "text": text, "roman": roman,
                "gloss": {"en": en}, "source": "krdict", "license": krdict.LICENSE,
                "source_ref": f"krdict:{code}#1", "review": "needs_review"}  # fmt: skip
        unit = {"id": f"ko-{n:03d}-u", "title": {"en": "U"}, "level": "topik1", "items": [item]}
        (course / rel).write_text(yaml.safe_dump(unit, allow_unicode=True), encoding="utf-8")
        meta["units"].append(rel)
    (course / "course.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True), "utf-8")
    return course


def _entry(code, word, pos, en, id_=None):
    sense = krdict.Sense(number=1, en=en, id=id_)
    return krdict.KrdictEntry(
        target_code=code, word=word, homonym=0, pos=pos, unit="단어",
        grade="초급", pronunciation=None, category=None, senses=[sense],
    )  # fmt: skip


def test_generate_writes_valid_attributed_sentences_and_never_clobbers(tmp_path):
    course = _course(tmp_path)
    pairs = [
        tatoeba.Pair(
            tatoeba.Sentence(1, "밥 먹었어요?", "minsu", tatoeba.CC_BY),
            tatoeba.Sentence(10, "Have you eaten?", "anna", tatoeba.CC_BY),
            None,
        )
    ]
    cands = sentences.tatoeba_candidates(pairs) + sentences.krdict_candidates(
        [krdict.Example(target_code=29602, sense=1, n=1, text="물을 마셨다.")]
    )
    entries = [_entry(20279, "밥", "명사", "rice"), _entry(34869, "먹다", "동사", "eat"),
               _entry(29602, "물", "명사", "water"), _entry(7, "마시다", "동사", "drink", "minum"),
               _entry(8, "많이", "부사", "a lot")]  # fmt: skip
    asked = []

    def run(prompt):
        asked.append(prompt)
        ids = [line.split(" | ")[0] for line in prompt.splitlines() if line.startswith("ko.s.")]
        return json.dumps({"items": {i: {"en": f"EN {i}", "id": f"ID {i}"} for i in ids}})

    src = (cands, entries, {"kept": 1}, 1)
    kw = {"courses": tmp_path, "sources": src, "run": run, "cache_dir": tmp_path / "llm"}
    s = sentences.generate("ko-en", min_known_ratio=0.8, **kw)
    assert s.added == {"units/011-u.yaml": ["ko.s.t1"], "units/012-u.yaml": ["ko.s.k29602-1-1"]}
    errors, units = validate_course_dir(course)
    assert errors == []
    t1 = units[1]["items"][1]
    assert t1["gloss"] == {"en": "Have you eaten?", "id": "ID ko.s.t1"}
    assert t1["tokens"] == ["밥", "먹었어요"] and t1["roman"] == "bap meogeosseoyo?"
    assert t1["author"] == "minsu" and t1["source_ref"] == "tatoeba:1"
    assert t1["gloss_sources"]["en"] == {"source": "tatoeba", "license": tatoeba.CC_BY,
                                         "author": "anna", "source_ref": "tatoeba:10"}  # fmt: skip
    assert t1["gloss_sources"]["id"]["source"] == "boso" and t1["review"] == "needs_review"
    k = units[2]["items"][1]
    assert k["gloss"]["en"] == "EN ko.s.k29602-1-1" and "author" not in k
    assert k["hints"] == [{"token": "마셨다", "gloss": {"en": "drink", "id": "minum"}}]
    assert check(t1, "item", "t1") == []

    credits = {e["source"]: e for e in pack.attribution(units)}
    assert credits["tatoeba"]["authors"] == ["anna", "minsu"]
    assert credits["boso"]["items"] == 2

    # Again: nothing new, nothing changed, no new LLM calls (cached).
    edited = course / "units/011-u.yaml"
    edited.write_text(edited.read_text(encoding="utf-8").replace("ID ko.s.t1", "Sudah makan?"))
    calls = len(asked)
    again = sentences.generate("ko-en", min_known_ratio=0.8, **kw)
    assert again.added == {} and len(asked) == calls
    assert "Sudah makan?" in edited.read_text(encoding="utf-8")


def test_hints_pick_the_common_homograph_of_the_right_class():
    glosses = sentences.hint_glosses(
        [_entry(1, "일", "의존 명사", "il"),
         krdict.KrdictEntry(**{**_entry(2, "일", "명사", "work").model_dump(),
                               "senses": [krdict.Sense(number=n, en="work", id=None)
                                          for n in (1, 2)]}),
         _entry(3, "일", "수사", "one"), _entry(4, "더하다", "동사", "add")]
    )  # fmt: skip
    assert glosses[("일", "N")] == {"en": "work"} and glosses[("일", "D")] == {"en": "one"}
    placed = sentences.place([_cand("k", "십에 십을 더하면 이십이다.")], [{"items": [
        _word("ko.w.sip", "십"), _word("ko.w.isip", "이십")]}], 1, 0.8, pos={})  # fmt: skip
    item = sentences.to_item(placed[0], sentences.Translation(en="a", id="b"), glosses)
    assert item["hints"] == [{"token": "더하면", "gloss": {"en": "add"}}]  # not 더 "more"


def test_schema_accepts_sentence_credits_and_rejects_bad_ones():
    item = {"id": "ko.s.t1", "type": "sentence", "text": "밥 먹었어요?", "roman": "bap",
            "tokens": ["밥", "먹었어요"], "gloss": {"en": "Ate?"}, "source": "tatoeba",
            "license": tatoeba.CC_BY, "author": "minsu", "review": "needs_review",
            "gloss_sources": {"en": {"source": "tatoeba", "license": tatoeba.CC_BY,
                                     "author": "anna"}, "id": {"source": "boso",
                                                               "license": "CC BY-SA 4.0"}},
            "hints": [{"token": "밥", "gloss": {"en": "rice"}}]}  # fmt: skip
    assert check(item, "item", "i") == []
    assert check({**item, "gloss_sources": {"fr": {"source": "x", "license": "y"}}}, "item", "i")
    assert check({**item, "gloss_sources": {"en": {"source": "x"}}}, "item", "i")
    assert check({**item, "hints": [{"token": "밥"}]}, "item", "i")

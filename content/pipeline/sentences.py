"""`pipeline sentences ko-en`: Tatoeba + krdict example sentences → vocab units.

A sentence goes into the earliest vocab unit where at most `max_unknown` of its content words
(nouns, verbs, adjectives, adverbs, …; verbs and adjectives as -다 lemmas) are not taught yet, and
at least `min_known_ratio` of all its morphemes (particles and endings count as known,
punctuation not at all) are. Hangul units (001–009) get no sentences.

No Korean is written by an LLM. Missing translations (all krdict examples, almost every
Indonesian one) come from `claude -p` via prompts/translate-sentences.v1.md and are credited to
boso. Existing items are never changed; new sentences are only appended.
"""

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from pipeline import fetch, overrides
from pipeline.build import CACHE, COURSES, dump_yaml, load_yaml
from pipeline.group import LLM_CACHE, _ask, _json_object, _template, run_claude
from pipeline.importers import krdict, tatoeba
from pipeline.nlp.ko import romanize

# Content morphemes by word class, so homographs don't match: 일 "one" (NR) is not 일 "work" (NNG).
CLASSES = {
    "NNG": "N", "NNP": "N", "NP": "N", "XR": "N",
    "NR": "D", "MM": "D",  # numerals and determiners: 일, 한, 이 (this)
    "VV": "V", "VA": "V",
    "MAG": "A",
}  # fmt: skip
KRDICT_CLASSES = {
    "명사": "N", "대명사": "N", "의존 명사": "N",
    "수사": "D", "관형사": "D",
    "동사": "V", "형용사": "V",
    "부사": "A",
}  # fmt: skip
# Latin letters, hanja, digits: not for a Korean course (and digits don't romanize or speak well).
FOREIGN_TAGS = {"SL", "SH", "SN"}
TRANSLATE_TEMPLATE = "translate-sentences.v1"
BATCH = 15
BOSO = {"source": "boso", "license": "CC BY-SA 4.0"}


@dataclass(frozen=True)
class Analysis:
    lemmas: tuple[tuple[str, str, int], ...]  # content (lemma, class, eojeol index)
    total: int  # morphemes, punctuation excluded
    foreign: bool
    derived: frozenset[str] = frozenset()  # lemmas followed by -하다 (더 + 하 → 더하다)


@dataclass
class Candidate:
    id: str
    text: str
    source: str
    license: str
    source_ref: str
    author: str | None = None
    en: dict | None = None  # {"text", "author", "license", "source_ref"} from Tatoeba
    ind: dict | None = None


@dataclass
class Placed:
    candidate: Candidate
    unit: int  # index into the vocab units
    unknown: list[tuple[str, str]]  # (lemma, class) not taught yet
    own: bool  # uses a word of its own unit
    analysis: Analysis


@dataclass
class Summary:
    sources: Counter = field(default_factory=Counter)
    coverage: dict[int, list[Counter]] = field(default_factory=dict)  # max_unknown → per unit
    added: dict[str, list[str]] = field(default_factory=dict)  # unit file → new item IDs
    translated: int = 0


@cache
def _kiwi():
    from kiwipiepy import Kiwi

    return Kiwi()


def lemma(form: str, tag: str) -> str:
    return form + "다" if tag in ("VV", "VA") else form


def eojeols(text: str) -> list[str]:
    return text.split()


def tokens(text: str) -> list[str]:
    """Word-bank cards: eojeols without surrounding punctuation."""
    return [t for e in eojeols(text) if (t := re.sub(r"^[^\w]+|[^\w]+$", "", e))]


def analyze(text: str) -> Analysis:
    starts = [m.start() for m in re.finditer(r"\S+", text)]
    lemmas, total, foreign, derived = [], 0, False, set()
    morphemes = _kiwi().tokenize(text)
    for n, t in enumerate(morphemes):
        tag = t.tag.split("-")[0]  # VV-R / VV-I → VV
        after = morphemes[n + 1].tag if n + 1 < len(morphemes) else ""
        if tag in CLASSES and after in ("XSV", "XSA"):
            derived.add(t.form)
        foreign |= tag in FOREIGN_TAGS
        if tag.startswith("S"):
            continue
        total += 1
        if tag in CLASSES:
            word = sum(s <= t.start for s in starts) - 1
            lemmas.append((lemma(t.form, tag), CLASSES[tag], word))
    return Analysis(tuple(lemmas), total, foreign, frozenset(derived))


def known_words(items: list[dict], pos: dict[str, str]) -> set[tuple[str, str]]:
    """(lemma, class) pairs a learner knows after these word items.

    The class comes from krdict's part of speech (`pos`: item ID → 품사) when there is one; the
    parts Kiwi finds in a word are known too (공부하다 → 공부), unless Kiwi just returns the word
    itself, whose class krdict knows better."""
    out = set()
    for item in items:
        text = item["text"]
        cls = KRDICT_CLASSES.get(pos.get(item["id"], ""))
        parts = {(lem, c) for lem, c, _ in analyze(text).lemmas}
        if cls:
            out.add((text, cls))
        if not cls or {lem for lem, _ in parts} != {text}:
            out |= parts
    return out


def place(
    candidates: list[Candidate],
    units: list[dict],
    max_unknown: int = 1,
    min_known_ratio: float = 0.9,
    max_eojeol: int = 8,
    pos: dict[str, str] | None = None,
) -> list[Placed]:
    """Each candidate in the earliest unit it fits, or nowhere."""
    own = [known_words([i for i in u["items"] if i["type"] == "word"], pos or {}) for u in units]
    known, so_far = [], set()
    for words in own:
        so_far = so_far | words
        known.append(so_far)
    out = []
    for c in candidates:
        if not 2 <= len(eojeols(c.text)) <= max_eojeol:
            continue
        a = analyze(c.text)
        if a.foreign or not a.lemmas:
            continue
        for k, words in enumerate(known):
            unknown = [(lem, cls) for lem, cls, _ in a.lemmas if (lem, cls) not in words]
            if len(set(unknown)) <= max_unknown and 1 - len(unknown) / a.total >= min_known_ratio:
                hit = any((lem, cls) in own[k] for lem, cls, _ in a.lemmas)
                out.append(Placed(c, k, sorted(set(unknown)), hit, a))
                break
    return out


def select(placed: list[Placed], per_unit: int, units: list[dict]) -> dict[int, list[Placed]]:
    """Up to `per_unit` per unit: own-unit words first, then human translations, short, by ID.

    One sentence per set of content words in a unit (밥 먹었어? / 밥 먹었어요? are one)."""
    taken = {i["id"] for u in units for i in u["items"]}
    seen_texts = {i["text"] for u in units for i in u["items"]}
    seen_words: set[tuple] = set()
    count = [0] * len(units)
    for k, u in enumerate(units):  # sentences already in a unit count, and are not repeated
        for i in u["items"]:
            if i["type"] == "sentence":
                count[k] += 1
                lemmas = frozenset(lem for lem, _, _ in analyze(i["text"]).lemmas)
                seen_words |= {(k, lemmas), (k, i["gloss"]["en"])}
    out: dict[int, list[Placed]] = {}
    order = sorted(
        placed,
        key=lambda p: (
            p.unit,
            not p.own,
            p.candidate.en is None,
            len(eojeols(p.candidate.text)),
            len(p.candidate.text),
            p.candidate.id,
        ),
    )
    for p in order:
        c = p.candidate
        words = (p.unit, frozenset(lem for lem, _, _ in p.analysis.lemmas))
        en = (p.unit, c.en["text"]) if c.en else None  # 내 딸이야 / 제 딸입니다: same gloss
        if c.id in taken or c.text in seen_texts or words in seen_words or en in seen_words:
            continue
        if count[p.unit] >= per_unit:
            continue
        count[p.unit] += 1
        seen_texts.add(c.text)
        seen_words |= {words, en} - {None}
        out.setdefault(p.unit, []).append(p)
    return out


def tatoeba_candidates(pairs: list[tatoeba.Pair]) -> list[Candidate]:
    def credit(s: tatoeba.Sentence | None) -> dict | None:
        if s is None:
            return None
        return {"text": s.text, "author": s.author, "license": s.license, "ref": s.source_ref}

    return [
        Candidate(
            id=f"ko.s.t{p.kor.id}",
            text=p.kor.text,
            source=tatoeba.SOURCE,
            license=p.kor.license,
            source_ref=p.kor.source_ref,
            author=p.kor.author,
            en=credit(p.eng),
            ind=credit(p.ind),
        )
        for p in pairs
    ]


def krdict_candidates(examples: list[krdict.Example]) -> list[Candidate]:
    return [
        Candidate(
            id=f"ko.s.k{e.target_code}-{e.sense}-{e.n}",
            text=e.text,
            source=krdict.SOURCE,
            license=krdict.LICENSE,
            source_ref=e.source_ref,
        )
        for e in examples
    ]


class Translation(BaseModel):
    en: str = Field(min_length=1)
    id: str = Field(min_length=1)


class Translations(BaseModel):
    items: dict[str, Translation]


def parse_translations(text: str, ids: set[str]) -> dict[str, Translation]:
    try:
        items = Translations.model_validate_json(_json_object(text)).items
    except ValidationError as e:
        raise ValueError(str(e)) from e
    if set(items) != ids:
        missing, extra = sorted(ids - set(items)), sorted(set(items) - ids)
        raise ValueError(f"translations don't match: missing {missing}, extra {extra}")
    for item_id, t in items.items():
        if not t.en.strip() or not t.id.strip():
            raise ValueError(f"empty translation for {item_id}")
    return items


def translate(
    candidates: list[Candidate],
    run: Callable[[str], str] = run_claude,
    cache_dir: Path = LLM_CACHE,
) -> dict[str, Translation]:
    """EN + ID for sentences missing either; batches of BATCH, cached, validated, retried once."""
    todo = [c for c in candidates if c.en is None or c.ind is None]
    out: dict[str, Translation] = {}
    for start in range(0, len(todo), BATCH):
        batch = todo[start : start + BATCH]
        lines = [f"{c.id} | {c.text} | {c.en['text'] if c.en else '-'}" for c in batch]
        prompt = _template(TRANSLATE_TEMPLATE).format(sentences="\n".join(lines))
        ids = {c.id for c in batch}
        parse = lambda t, ids=ids: parse_translations(t, ids)  # noqa: E731
        out.update(_ask(TRANSLATE_TEMPLATE, prompt, parse, run, cache_dir))
    return out


def _credit(found: dict | None) -> dict:
    if found is None:
        return dict(BOSO)
    return {
        "source": tatoeba.SOURCE,
        "license": found["license"],
        "author": found["author"],
        "source_ref": found["ref"],
    }


def to_item(p: Placed, t: Translation | None, glosses: dict[tuple[str, str], dict]) -> dict:
    c = p.candidate
    words = eojeols(c.text)
    hints = []
    for lem, cls in p.unknown:
        # 더하면 is 더하다 (to add), not 더 (more): look derived words up whole, or give no hint.
        derived = lem in p.analysis.derived
        g = glosses.get((lem + "하다", "V")) if derived else glosses.get((lem, cls))
        word = next(w for x, c, w in p.analysis.lemmas if (x, c) == (lem, cls))
        token = re.sub(r"^[^\w]+|[^\w]+$", "", words[word])
        if g and token:
            hints.append({"token": token, "gloss": g})
    item = {
        "id": c.id,
        "type": "sentence",
        "text": c.text,
        "roman": romanize(c.text),
        "tokens": tokens(c.text),
        "gloss": {
            "en": c.en["text"] if c.en else t.en,
            "id": c.ind["text"] if c.ind else t.id,
        },
        "gloss_sources": {"en": _credit(c.en), "id": _credit(c.ind)},
    }
    if hints:
        item["hints"] = hints
    item |= {"source": c.source, "license": c.license}
    if c.author:
        item["author"] = c.author
    return item | {"source_ref": c.source_ref, "review": "needs_review"}


def hint_glosses(entries: list[krdict.KrdictEntry]) -> dict[tuple[str, str], dict]:
    """(word, class) → {en, id} of its first sense with an English gloss.

    Homographs of the same class: the entry with the most senses (the common, basic one), as in
    build.select_pool."""
    out: dict[tuple[str, str], dict] = {}
    for e in sorted(entries, key=lambda e: (-len(e.senses), e.target_code)):
        sense = next((s for s in e.senses if s.en), None)
        key = (e.word, KRDICT_CLASSES.get(e.pos, ""))
        if sense and key not in out:
            out[key] = {"en": sense.en} | ({"id": sense.id} if sense.id else {})
    return out


def load_sources(cache_dir: Path = CACHE):
    zip_path = fetch.check("krdict")
    digest = fetch.sha256(zip_path)[:16]
    examples = krdict.load_examples(zip_path, cache_dir / f"krdict-examples-{digest}.json")
    beginner, _ = krdict.load_beginner(zip_path, cache_dir / f"krdict-{digest}.json")
    files = {
        Path(r).name.split(".")[0]: fetch.check(fetch.tatoeba_key(r)) for r in fetch.TATOEBA_FILES
    }
    pairs, stats = tatoeba.load(files)
    return tatoeba_candidates(pairs) + krdict_candidates(examples), beginner, stats, len(examples)


def coverage(placed: list[Placed], n_units: int) -> list[Counter]:
    out = [Counter() for _ in range(n_units)]
    for p in placed:
        out[p.unit][p.candidate.source] += 1
    return out


def generate(
    course_id: str,
    max_unknown: int = 1,
    min_known_ratio: float = 0.9,
    max_eojeol: int = 8,
    per_unit: int = 6,
    dry_run: bool = False,
    courses: Path = COURSES,
    sources=None,
    run: Callable[[str], str] = run_claude,
    cache_dir: Path = LLM_CACHE,
) -> Summary:
    if course_id != "ko-en":
        raise ValueError(f"sentences only supports ko-en for now, not {course_id}")
    course_dir = courses / course_id
    course = load_yaml(course_dir / "course.yaml")
    files = [rel for rel in course["units"]]
    units = [load_yaml(course_dir / rel) for rel in files]
    vocab = [(rel, u) for rel, u in zip(files, units, strict=True) if u.get("kind") != "script"]
    candidates, beginner, stats, n_examples = sources or load_sources()
    summary = Summary()
    summary.sources.update(stats)
    summary.sources["krdict examples"] = n_examples

    vocab_units = [u for _, u in vocab]
    by_code = {e.target_code: e.pos for e in beginner}
    pos = {
        i["id"]: by_code[int(m[1])]
        for u in vocab_units
        for i in u["items"]
        if (m := re.fullmatch(r"krdict:(\d+)#\d+", i.get("source_ref", "")))
        and int(m[1]) in by_code
    }
    for n in sorted({0, max_unknown}):
        placed_n = place(candidates, vocab_units, n, min_known_ratio, max_eojeol, pos)
        summary.coverage[n] = coverage(placed_n, len(vocab_units))
    placed = place(candidates, vocab_units, max_unknown, min_known_ratio, max_eojeol, pos)

    chosen = select(placed, per_unit, vocab_units)
    new = [p for ps in chosen.values() for p in ps]
    if dry_run:
        for k, ps in sorted(chosen.items()):
            if ps:
                summary.added[vocab[k][0]] = [p.candidate.id for p in ps]
        return summary

    trans = translate([p.candidate for p in new], run, cache_dir)
    summary.translated = len(trans)
    glosses = hint_glosses(beginner)
    hs = overrides.load_hints(course_dir)
    by_entry = {e.target_code: e for e in beginner}
    fix = lambda item: overrides.apply_hints(hs, item, by_entry)[0]  # noqa: E731
    for k, ps in sorted(chosen.items()):
        if not ps:
            continue
        rel, unit = vocab[k]
        unit["items"] += [fix(to_item(p, trans.get(p.candidate.id), glosses)) for p in ps]
        dump_yaml(unit, course_dir / rel)
        summary.added[rel] = [p.candidate.id for p in ps]
    return summary

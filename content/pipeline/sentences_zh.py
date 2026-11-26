"""`pipeline sentences zh-en`: Tatoeba Mandarin sentences → HSK vocab units.

Words come from jieba. A sentence goes into the earliest vocab unit where at most `max_unknown`
of its words are not taught yet (a word counts as known when it is a taught word, or every
character of it is one) and at least `min_known_ratio` of its characters are known. Only
simplified, all-Chinese sentences are used (no Latin letters or digits). Pinyin comes from the
taught word when there is one, else pypinyin. Hints for the new word come from CC-CEDICT.

No Chinese is written by an LLM. Missing translations come from `claude -p` via
prompts/translate-sentences-zh.v1.md and are credited to boso. Existing items are never changed.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from pipeline import fetch
from pipeline.build import COURSES, dump_yaml, load_yaml
from pipeline.group import LLM_CACHE, run_claude
from pipeline.importers import cedict, tatoeba
from pipeline.sentences import (
    Candidate,
    Summary,
    Translation,
    _credit,
    tatoeba_candidates,
    translate,
)

TEMPLATE = "translate-sentences-zh.v1"
HAN = re.compile(r"[一-鿿]")
PUNCT = {"，": ",", "。": ".", "？": "?", "！": "!", "、": ",", "：": ":", "；": ";"}
ALLOWED = re.compile(r"^[一-鿿，。？！、：；]+$")


@cache
def _jieba():
    import logging

    import jieba

    jieba.setLogLevel(logging.WARNING)
    return jieba


def words(text: str) -> list[str]:
    """Word-bank cards: jieba words without punctuation."""
    return [w for w in _jieba().lcut(text) if HAN.search(w)]


def pinyin(word: str) -> str:
    from pypinyin import Style, lazy_pinyin

    return "".join(lazy_pinyin(word, style=Style.TONE))


def roman(text: str, taught: dict[str, str]) -> str:
    """Pinyin, one space-separated word per card, punctuation on the word before it."""
    out: list[str] = []
    for w in _jieba().lcut(text):
        if HAN.search(w):
            out.append(taught.get(w) or pinyin(w))
        elif out:
            out[-1] += "".join(PUNCT.get(c, c) for c in w)
    if out:
        out[0] = out[0][0].upper() + out[0][1:]
    return " ".join(out)


def traditional_only(entries: list[cedict.Entry]) -> set[str]:
    """Characters only written in traditional script (說, not 说): such sentences are skipped."""
    simp = {e.simp for e in entries if len(e.simp) == 1}
    return {e.trad for e in entries if len(e.trad) == 1 and e.trad != e.simp} - simp


@dataclass
class Placed:
    candidate: Candidate
    unit: int
    unknown: list[str]
    own: bool


def place(
    candidates: list[Candidate],
    units: list[dict],
    trad: set[str],
    max_unknown: int = 1,
    min_known_ratio: float = 0.9,
    max_words: int = 10,
) -> list[Placed]:
    own = [{i["text"] for i in u["items"] if i["type"] == "word"} for u in units]
    known, so_far = [], set()
    for taught in own:
        so_far = so_far | taught
        known.append(so_far)
    out = []
    for c in candidates:
        if not ALLOWED.match(c.text) or trad & set(c.text):
            continue
        ws = words(c.text)
        if not 3 <= len(ws) <= max_words:  # 2 cards make no word-bank exercise
            continue
        chars = "".join(ws)
        for k, taught in enumerate(known):
            unknown = sorted({w for w in ws if w not in taught and not set(w) <= taught})
            known_chars = sum(ch in taught or w in taught for w in ws for ch in w)
            if len(unknown) <= max_unknown and known_chars / len(chars) >= min_known_ratio:
                out.append(Placed(c, k, unknown, any(w in own[k] for w in ws)))
                break
    return out


def select(placed: list[Placed], per_unit: int, units: list[dict]) -> dict[int, list[Placed]]:
    """Up to `per_unit` per unit: own-unit words first, then human translations, short, by ID."""
    taken = {i["id"] for u in units for i in u["items"]}
    seen = {i["text"] for u in units for i in u["items"]}
    seen |= {i["gloss"]["en"] for u in units for i in u["items"] if i["type"] == "sentence"}
    count = [sum(i["type"] == "sentence" for i in u["items"]) for u in units]
    out: dict[int, list[Placed]] = {}
    order = sorted(
        placed,
        key=lambda p: (
            p.unit,
            not p.own,
            p.candidate.en is None,
            len(p.candidate.text),
            p.candidate.id,
        ),
    )
    for p in order:
        c = p.candidate
        en = c.en["text"] if c.en else None
        if c.id in taken or c.text in seen or en in seen or count[p.unit] >= per_unit:
            continue
        count[p.unit] += 1
        seen |= {c.text, en} - {None}
        out.setdefault(p.unit, []).append(p)
    return out


def hint_glosses(entries: list[cedict.Entry]) -> dict[str, str]:
    """word → its first teachable CC-CEDICT sense (lowercase readings first: not surnames)."""
    out: dict[str, str] = {}
    for e in sorted(entries, key=lambda e: e.pinyin[:1].isupper()):
        if e.simp not in out:
            sense = next((d for _, d in cedict.senses([e])), None)
            if sense:
                out[e.simp] = cedict.clean(sense)
    return out


def to_item(p: Placed, t: Translation | None, taught: dict[str, str], hints: dict[str, str]):
    c = p.candidate
    item = {
        "id": c.id,
        "type": "sentence",
        "text": c.text,
        "roman": roman(c.text, taught),
        "tokens": words(c.text),
        "gloss": {
            "en": c.en["text"] if c.en else t.en,
            "id": c.ind["text"] if c.ind else t.id,
        },
        "gloss_sources": {"en": _credit(c.en), "id": _credit(c.ind)},
    }
    found = [{"token": w, "gloss": {"en": hints[w]}} for w in p.unknown if w in hints]
    if found:
        item["hints"] = found
    item |= {"source": c.source, "license": c.license}
    if c.author:
        item["author"] = c.author
    return item | {"source_ref": c.source_ref, "review": "needs_review"}


def load_sources():
    files = {
        Path(r).name.split(".")[0]: fetch.check(fetch.tatoeba_key(r)) for r in fetch.TATOEBA_FILES
    }
    pairs, stats = tatoeba.load(files, "cmn")
    return tatoeba_candidates(pairs, "zh"), cedict.load(fetch.check("cedict")), stats


def generate(
    max_unknown: int = 1,
    min_known_ratio: float = 0.9,
    max_words: int = 10,
    per_unit: int = 6,
    dry_run: bool = False,
    courses: Path = COURSES,
    sources=None,
    run: Callable[[str], str] = run_claude,
    cache_dir: Path = LLM_CACHE,
) -> Summary:
    course_dir = courses / "zh-en"
    files = load_yaml(course_dir / "course.yaml")["units"]
    units = [load_yaml(course_dir / rel) for rel in files]
    vocab = [(rel, u) for rel, u in zip(files, units, strict=True) if u.get("kind") != "script"]
    vocab_units = [u for _, u in vocab]
    candidates, entries, stats = sources or load_sources()
    summary = Summary()
    summary.sources.update(stats)
    trad = traditional_only(entries)
    for n in sorted({0, max_unknown}):
        found = place(candidates, vocab_units, trad, n, min_known_ratio, max_words)
        per = [0] * len(vocab_units)
        for p in found:
            per[p.unit] += 1
        summary.coverage[n] = [{"tatoeba": x, "krdict": 0} for x in per]
    placed = place(candidates, vocab_units, trad, max_unknown, min_known_ratio, max_words)
    chosen = select(placed, per_unit, vocab_units)
    if dry_run:
        for k, ps in sorted(chosen.items()):
            summary.added[vocab[k][0]] = [p.candidate.id for p in ps]
        return summary

    new = [p.candidate for ps in chosen.values() for p in ps]
    trans = translate(new, run, cache_dir, TEMPLATE)
    summary.translated = len(trans)
    taught = {i["text"]: i["roman"] for u in vocab_units for i in u["items"] if i["type"] == "word"}
    hints = hint_glosses(entries)
    for k, ps in sorted(chosen.items()):
        rel, unit = vocab[k]
        unit["items"] += [to_item(p, trans.get(p.candidate.id), taught, hints) for p in ps]
        dump_yaml(unit, course_dir / rel)
        summary.added[rel] = [p.candidate.id for p in ps]
    return summary

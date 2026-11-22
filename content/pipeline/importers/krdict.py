"""Import 한국어기초사전 (krdict) entries from the full JSON dump (LMF structure)."""

import json
import re
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

SOURCE = "krdict"
LICENSE = "CC BY-SA 2.0 KR"
# Not vocabulary words a learner studies on their own.
EXCLUDED_POS = {"접사", "조사", "어미", "보조 동사", "보조 형용사", "품사 없음"}


class Sense(BaseModel):
    number: int
    en: str | None
    id: str | None


class KrdictEntry(BaseModel):
    target_code: int
    word: str
    homonym: int
    pos: str
    unit: str  # 단어 (word) or 구 (phrase)
    grade: str  # 초급 / 중급 / 고급 / 없음
    pronunciation: str | None
    category: str | None
    senses: list[Sense]

    @property
    def source_ref(self) -> str:
        return f"{SOURCE}:{self.target_code}#{self.senses[0].number}"


def _list(x) -> list:
    return x if isinstance(x, list) else [] if x is None else [x]


def _feats(node: dict) -> dict[str, list[str]]:
    out = defaultdict(list)
    for f in _list(node.get("feat")):
        if "val" in f:
            out[f["att"]].append(f["val"])
    return out


def short_gloss(lemma: str | None) -> str | None:
    """'eat; have; consume' → 'eat, have'. Placeholders like '(no equivalent)' → None."""
    if not lemma:
        return None
    lemma = lemma.strip()
    if not lemma or (lemma.startswith("(") and lemma.endswith(")")):
        return None
    parts = [p.strip() for p in re.split(r"[;,]", lemma) if p.strip()]
    return ", ".join(parts[:2]) or None


def parse_entry(raw: dict) -> KrdictEntry:
    f = _feats(raw)
    senses = []
    for s in _list(raw.get("Sense")):
        equivalents = {}
        for eq in _list(s.get("Equivalent")):
            e = _feats(eq)
            if e["language"] and e["lemma"]:
                equivalents[e["language"][0]] = e["lemma"][0]
        senses.append(
            Sense(
                number=int(s.get("val", len(senses) + 1)),
                en=short_gloss(equivalents.get("영어")),
                id=short_gloss(equivalents.get("인도네시아어")),
            )
        )
    senses.sort(key=lambda s: s.number)
    pronunciation = next(
        (
            w["pronunciation"][0]
            for w in map(_feats, _list(raw.get("WordForm")))
            if w["type"] == ["발음"] and w["pronunciation"]
        ),
        None,
    )
    return KrdictEntry(
        target_code=int(raw["val"]),
        word=next(v for lemma in _list(raw["Lemma"]) for v in _feats(lemma)["writtenForm"]),
        homonym=int((f["homonym_number"] or ["0"])[0]),
        pos=(f["partOfSpeech"] or ["품사 없음"])[0],
        unit=(f["lexicalUnit"] or ["단어"])[0],
        grade=(f["vocabularyLevel"] or ["없음"])[0],
        pronunciation=pronunciation,
        category=(f["semanticCategory"] or [None])[0],
        senses=senses,
    )


def iter_entries(zip_path: Path) -> Iterator[KrdictEntry]:
    """All entries of the dump, file by file (each file is ~100 MB, so one at a time)."""
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(z.namelist(), key=lambda n: int(n.split("_")[0])):
            if not name.endswith(".json"):
                continue
            data = json.loads(z.read(name))
            for raw in data["LexicalResource"]["Lexicon"]["LexicalEntry"]:
                yield parse_entry(raw)


def load_beginner(zip_path: Path, cache: Path | None = None) -> tuple[list[KrdictEntry], int]:
    """초급 entries and the total entry count. Parsing the dump is slow, so cache it by checksum."""
    if cache and cache.is_file():
        data = json.loads(cache.read_text(encoding="utf-8"))
        return [KrdictEntry.model_validate(e) for e in data["entries"]], data["total"]
    total, beginner = 0, []
    for entry in iter_entries(zip_path):
        total += 1
        if entry.grade == "초급":
            beginner.append(entry)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        data = {"total": total, "entries": [e.model_dump() for e in beginner]}
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return beginner, total


def vocabulary_candidates(entries: list[KrdictEntry]) -> tuple[list[KrdictEntry], Counter]:
    """Single words with a real part of speech and an English gloss on the first sense."""
    stats: Counter = Counter(beginner=len(entries))
    out = []
    for e in entries:
        if e.unit != "단어":
            stats["dropped: phrase"] += 1
        elif e.pos in EXCLUDED_POS:
            stats[f"dropped: {e.pos}"] += 1
        elif not e.senses or not e.senses[0].en:
            stats["dropped: no en gloss"] += 1
        else:
            out.append(e)
    stats["candidates"] = len(out)
    stats["with id gloss"] = sum(1 for e in out if e.senses[0].id)
    return out, stats


class Example(BaseModel):
    """A 문장 example of one sense of a 초급 entry. The dump has no translations for these."""

    target_code: int
    sense: int
    n: int  # position among that sense's sentence examples, from 1
    text: str

    @property
    def source_ref(self) -> str:
        return f"{SOURCE}:{self.target_code}#{self.sense}/{self.n}"


def parse_examples(raw: dict) -> list[Example]:
    out = []
    for s in _list(raw.get("Sense")):
        sense = int(s.get("val", 0))
        sentences = [
            e["example"][0]
            for e in map(_feats, _list(s.get("SenseExample")))
            if e["type"] == ["문장"] and e["example"]
        ]
        out += [
            Example(target_code=int(raw["val"]), sense=sense, n=n, text=text.strip())
            for n, text in enumerate(sentences, 1)
        ]
    return out


def load_examples(zip_path: Path, cache: Path | None = None) -> list[Example]:
    """Sentence examples of 초급 entries (cached by checksum, like load_beginner)."""
    if cache and cache.is_file():
        return [Example.model_validate(e) for e in json.loads(cache.read_text(encoding="utf-8"))]
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(z.namelist()):
            if name.endswith(".json"):
                data = json.loads(z.read(name))
                for raw in data["LexicalResource"]["Lexicon"]["LexicalEntry"]:
                    if _feats(raw)["vocabularyLevel"] == ["초급"]:
                        out += parse_examples(raw)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps([e.model_dump() for e in out], ensure_ascii=False), "utf-8")
    return out

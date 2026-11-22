"""Tatoeba exports → Korean sentences with their English / Indonesian translations.

Only attributable, clean sentences are kept: an author (no orphans), no maintenance tags (`@change`,
`@needs native check`, … and `non-sentence`), and CC BY 2.0 FR or CC0. Tatoeba audio is never used.
"""

import bz2
import csv
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

SOURCE = "tatoeba"
URL = "https://tatoeba.org"
CC_BY = "CC BY 2.0 FR"
CC0 = "CC0 1.0"
TRANSLATIONS = ("eng", "ind")


@dataclass(frozen=True)
class Sentence:
    id: int
    text: str
    author: str
    license: str

    @property
    def source_ref(self) -> str:
        return f"{SOURCE}:{self.id}"


@dataclass(frozen=True)
class Pair:
    """A Korean sentence and its best direct translation per language (None if there is none)."""

    kor: Sentence
    eng: Sentence | None
    ind: Sentence | None


def bad_tag(tag: str) -> bool:
    return tag.startswith("@") or tag == "non-sentence"


def _rows(path: Path) -> Iterator[list[str]]:
    with bz2.open(path, "rt", encoding="utf-8", newline="") as f:
        yield from csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)


def _cc0(path: Path, wanted: set[int]) -> set[int]:
    with tarfile.open(path, "r:bz2") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith(".csv"))
        f = tar.extractfile(member)
        assert f is not None
        out = set()
        for line in f:
            sid = int(line.split(b"\t", 1)[0])
            if sid in wanted:
                out.add(sid)
        return out


def _sentences(path: Path, wanted: set[int] | None) -> dict[int, tuple[str, str]]:
    """{id: (text, author)} from a *_sentences_detailed file, orphans dropped."""
    out = {}
    for row in _rows(path):
        sid = int(row[0])
        if (wanted is None or sid in wanted) and row[3] not in ("", r"\N"):
            out[sid] = (row[2].strip(), row[3])
    return out


def load(files: dict[str, Path]) -> tuple[list[Pair], dict[str, int]]:
    """Clean Korean sentences with translations, and counts of what was dropped.

    `files` maps names (kor_sentences_detailed, kor-eng_links, …, sentences_CC0) to paths."""
    stats: dict[str, int] = {}
    tagged = {
        int(sid)
        for lang in ("kor", *TRANSLATIONS)
        for sid, tag in _rows(files[f"{lang}_tags"])
        if bad_tag(tag)
    }
    rows = list(_rows(files["kor_sentences_detailed"]))
    stats["kor sentences"] = len(rows)
    kor = _sentences(files["kor_sentences_detailed"], None)
    stats["dropped: no author"] = len(rows) - len(kor)
    stats["dropped: tag"] = len(kor.keys() & tagged)
    kor = {k: v for k, v in kor.items() if k not in tagged}

    links: dict[str, dict[int, int]] = {}
    for lang in TRANSLATIONS:
        best: dict[int, int] = {}
        for a, b in _rows(files[f"kor-{lang}_links"]):
            k, t = int(a), int(b)
            if k in kor and t not in tagged:
                best[k] = min(best.get(k, t), t)  # several translations: the oldest one
        links[lang] = best
    texts = {
        lang: _sentences(files[f"{lang}_sentences_detailed"], set(links[lang].values()))
        for lang in TRANSLATIONS
    }
    cc0 = _cc0(files["sentences_CC0"], set(kor) | {t for m in links.values() for t in m.values()})

    def sentence(sid: int, text_author: tuple[str, str]) -> Sentence:
        return Sentence(sid, *text_author, CC0 if sid in cc0 else CC_BY)

    pairs = []
    for sid in sorted(kor):
        trans = {}
        for lang in TRANSLATIONS:
            t = links[lang].get(sid)
            trans[lang] = sentence(t, texts[lang][t]) if t in texts[lang] else None
        pairs.append(Pair(sentence(sid, kor[sid]), trans["eng"], trans["ind"]))
    stats["kept"] = len(pairs)
    stats["with eng"] = sum(p.eng is not None for p in pairs)
    stats["with ind"] = sum(p.ind is not None for p in pairs)
    return pairs, stats

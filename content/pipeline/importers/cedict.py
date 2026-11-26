"""CC-CEDICT (CC BY-SA 4.0): `Trad Simp [pin1 yin1] /def 1/def 2/`, one entry a line."""

import gzip
import re
from dataclasses import dataclass
from pathlib import Path

SOURCE = "cc-cedict"
LICENSE = "CC BY-SA 4.0"
LINE = re.compile(r"^(\S+) (\S+) \[([^\]]*)\] /(.*)/\s*$")
# Definitions that don't teach the word: cross-references, variants, surnames, classifier notes.
SKIP = re.compile(
    r"^(surname |(old |unofficial |archaic |erhua |Japanese )?variant of |used in |see |"
    r"see also |CL:|abbr\. for |also written |also pr\. |old name for )",
    re.I,
)


@dataclass(frozen=True)
class Entry:
    trad: str
    simp: str
    pinyin: str  # numbered, as in the dictionary: "da3 dian4 hua4"
    defs: tuple[str, ...]

    @property
    def source_ref(self) -> str:
        return f"{SOURCE}:{self.simp}[{self.pinyin}]"


def parse(lines) -> list[Entry]:
    out = []
    for line in lines:
        if line.startswith("#") or not (m := LINE.match(line)):
            continue
        out.append(Entry(m[1], m[2], m[3], tuple(d for d in m[4].split("/") if d)))
    return out


def load(path: Path) -> list[Entry]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return parse(f)


# Notes a learner can't use: classifiers "(CL:個|个[ge4])", readings "(Taiwan pr. [han4])".
NOTE = re.compile(r"\s*\((?:CL:|[^()]*\bpr\.)[^()]*\)")
# A cross-reference "您[nin2]" or "樣|样[yang4]": keep the simplified characters.
XREF = re.compile(r"(?:[^\s|\[\]()]+\|)?([^\s|\[\]()]+)\[[a-zA-Z0-9:, ]+\]")


def clean(definition: str) -> str:
    """A definition as a gloss: without classifier and reading notes or pinyin cross-references."""
    return re.sub(r"\s+", " ", XREF.sub(r"\1", NOTE.sub("", definition))).strip()


def senses(entries: list[Entry]) -> list[tuple[Entry, str]]:
    """(entry, definition) pairs a word can be taught with, in dictionary order."""
    return [(e, d) for e in entries for d in e.defs if not SKIP.match(d)]

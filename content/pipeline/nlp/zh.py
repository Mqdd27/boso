"""Mandarin pinyin helpers: CC-CEDICT numbered pinyin (`dian4 hua4`) → tone marks (`diànhuà`)."""

MARKS = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}


def numbered(pinyin: str) -> list[str]:
    """CC-CEDICT pinyin as lower-case numbered syllables, `u:`/`v` written `ü`: ["nü3", "ren2"]."""
    return [s.lower().replace("u:", "ü").replace("v", "ü") for s in pinyin.split()]


def mark(syllable: str) -> str:
    """One numbered syllable with its tone mark: dian4 → diàn, nü3 → nǚ, de5 → de, r5 → r.

    The mark goes on a or e, on the o of ou, else on the last vowel (the standard rule)."""
    s = syllable.replace("u:", "ü").replace("v", "ü")
    tone = int(s[-1]) if s[-1].isdigit() else 5
    base = s.rstrip("012345")
    if tone not in (1, 2, 3, 4):
        return base
    low = base.lower()
    at = next((low.index(v) for v in "ae" if v in low), -1)
    if at < 0:
        at = low.index("o") if "ou" in low else max(low.rfind(v) for v in MARKS)
    if at < 0:  # no vowel (m2, ng2): leave it unmarked
        return base
    marked = MARKS[low[at]][tone - 1]
    return base[:at] + (marked.upper() if base[at].isupper() else marked) + base[at + 1 :]


def roman(pinyin: str) -> str:
    """A word's pinyin with tone marks, syllables joined: `da3 dian4 hua4` → `dǎdiànhuà`.

    An apostrophe goes before a, e or o that starts a later syllable (xī'ān)."""
    out = ""
    for n, s in enumerate(pinyin.split()):
        m = mark(s)
        if n and m[:1].lower() in "aeoāáǎàēéěèōóǒò":
            out += "'"
        out += m
    return out


def tones(pinyin: str) -> str:
    """The item's `tones` field: numbered syllables, tone 5 for neutral (`de5`, `r5`)."""
    return " ".join(s if s[-1].isdigit() else s + "5" for s in numbered(pinyin))


def slug(pinyin: str) -> str:
    """ID slug from numbered pinyin: `da3 dian4 hua4` → `da3dian4hua4`, `nü3` → `nv3`."""
    return tones(pinyin).replace(" ", "").replace("ü", "v")

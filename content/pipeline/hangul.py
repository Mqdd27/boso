"""`pipeline hangul <course>`: the Hangul script units (001–009) from courses/<course>/hangul.yaml.

Hand-written content (source: boso), no external data, no LLM, deterministic. Like `build`, it only
adds: an existing unit file is never rewritten (manual edits and reviewed items stay safe), it is
reported as kept when it differs from what would be generated.
"""

from dataclasses import dataclass, field
from pathlib import Path

from pipeline.build import dump_yaml, load_yaml
from pipeline.nlp.ko import FINALS, INITIALS, VOWELS, compose, decompose, romanize

SOURCE = "boso"
LICENSE = "CC BY-SA 4.0"
LEVEL = "topik1"


@dataclass
class Summary:
    written: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)  # exists and differs: left alone
    unchanged: list[str] = field(default_factory=list)
    readings: int = 0


def _item(item_id: str, text: str, roman: str, en: str, id_: str) -> dict:
    return {
        "id": item_id,
        "type": "char",
        "text": text,
        "roman": roman,
        "gloss": {"en": en, "id": id_},
        "source": SOURCE,
        "license": LICENSE,
        "review": "needs_review",
    }


def letter_item(letter: str, spec: dict) -> dict:
    return _item(f"ko.c.{spec['slug']}", letter, spec["roman"], spec["en"], spec["id"])


def syllable_item(syllable: str, finals: dict[str, str]) -> dict:
    parts = decompose(syllable)
    if parts is None:
        raise ValueError(f"{syllable!r} is not a Hangul syllable")
    initial, vowel, final = parts
    roman = romanize(syllable)
    en = f"syllable {roman}: {initial} + {vowel}"
    id_ = f"suku kata {roman}: {initial} + {vowel}"
    if final:
        en += f" + final {final}, read {finals[final]}"
        id_ += f" + akhir {final}, dibaca {finals[final]}"
    return _item(f"ko.c.syl-{roman}", syllable, roman, en, id_)


def reading(letter: str) -> str:
    """How a letter is read aloud: a consonant with ㅏ (ㄱ → 가), a vowel after ㅇ (ㅏ → 아)."""
    if letter in VOWELS:
        return compose("ㅇ", letter)
    if letter in INITIALS:
        return compose(letter, "ㅏ")
    raise ValueError(f"{letter!r} is not a Hangul letter")


def units(spec: dict) -> list[tuple[str, dict]]:
    """[(relative path, unit)] for every script unit in hangul.yaml, in order."""
    out = []
    for u in spec["units"]:
        name = f"{u['number']:03d}-{u['slug']}"
        items = [letter_item(c, spec["letters"][c]) for c in u.get("letters", [])]
        items += [syllable_item(s, spec["finals"]) for s in u.get("syllables", [])]
        unit = {
            "id": f"ko-{name}",
            "title": u["title"],
            "level": LEVEL,
            "kind": "script",
            "items": items,
        }
        out.append((f"units/{name}.yaml", unit))
    return out


def generate(course_dir: Path, dry_run: bool = False) -> Summary:
    spec = load_yaml(course_dir / "hangul.yaml")
    unknown = [f for f in spec["finals"] if f not in FINALS]
    if unknown:
        raise ValueError(f"not final consonants: {unknown}")
    summary = Summary()
    generated = units(spec)
    for rel, unit in generated:
        path = course_dir / rel
        if not path.is_file():
            summary.written.append(rel)
            if not dry_run:
                path.parent.mkdir(exist_ok=True)
                dump_yaml(unit, path)
        elif load_yaml(path) == unit:
            summary.unchanged.append(rel)
        else:
            summary.kept.append(rel)

    # Script units go first in course.yaml, in curriculum order; everything else keeps its order.
    course_file = course_dir / "course.yaml"
    course = load_yaml(course_file)
    script = [rel for rel, _ in generated]
    ordered = script + [rel for rel in course["units"] if rel not in script]

    # readings.yaml: what TTS reads for each letter. Existing entries win (hand-edited).
    readings_file = course_dir / "readings.yaml"
    readings = (load_yaml(readings_file) or {}) if readings_file.is_file() else {}
    for _, unit in generated:
        for item in unit["items"]:
            is_letter = decompose(item["text"]) is None
            if is_letter and item["id"] not in readings:
                readings[item["id"]] = reading(item["text"])
                summary.readings += 1
    if not dry_run:
        if ordered != course["units"]:
            course["units"] = ordered
            dump_yaml(course, course_file)
        if summary.readings:
            dump_yaml(dict(sorted(readings.items())), readings_file)
    return summary

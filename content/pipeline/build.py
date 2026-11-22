"""`pipeline build ko-en`: krdict → romanize → group + pick senses (claude -p) → units/*.yaml."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path

import yaml

from pipeline import fetch, overrides
from pipeline.group import group, pick_senses, run_claude
from pipeline.importers import krdict
from pipeline.nlp.ko import romanize, slugify

CONTENT = Path(__file__).resolve().parents[1]
COURSES = CONTENT / "courses"
CACHE = CONTENT / "cache"
FIRST_UNIT = 10  # 001–009 are reserved for the Hangul script units
POOL_SIZE = 250
LEVEL = "topik1"


@dataclass
class Summary:
    stats: Counter
    pool: int = 0
    existing_units: int = 0
    new_units: list[tuple[str, int]] = field(default_factory=list)  # (file, item count)
    overridden: list[str] = field(default_factory=list)  # existing items an override was applied to
    kept: list[str] = field(default_factory=list)  # overrides skipped: item reviewed or hand-edited


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(data, path: Path) -> None:
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    path.write_text(text, encoding="utf-8")


def core_entries(words: list[str], entries: list[krdict.KrdictEntry]) -> list:
    """Resolve core-words.yaml: `word` must match one candidate, `word#target_code` pins one."""
    by_word: dict[str, list] = {}
    for e in entries:
        by_word.setdefault(e.word, []).append(e)
    out = []
    for spec in words:
        word, _, code = str(spec).partition("#")
        matches = [e for e in by_word.get(word, []) if not code or str(e.target_code) == code]
        if len(matches) != 1:
            codes = ", ".join(f"{e.target_code} ({e.pos})" for e in by_word.get(word, []))
            raise ValueError(
                f"core word {spec!r} matches {len(matches)} candidates: {codes or '-'}"
            )
        out.append(matches[0])
    return out


def select_pool(entries: list[krdict.KrdictEntry], size: int = POOL_SIZE) -> list:
    """Deterministic pool of the most basic words.

    Within each top-level semantic category, words with more senses come first (a word with many
    senses is a common, basic word: 먹다 has 25, 하나 has 5); ties by krdict target_code. Then take
    one word per category in turn, so every theme gets candidates, until `size` words are picked.
    """
    by_category: dict[str, list] = {}
    for e in entries:
        top = (e.category or "기타").split(">")[0].strip()
        by_category.setdefault(top, []).append(e)
    columns = [
        sorted(words, key=lambda e: (-len(e.senses), e.target_code))
        for _, words in sorted(by_category.items())
    ]
    picked = [e for row in zip_longest(*columns) for e in row if e is not None]
    return picked[:size]


def to_item(entry: krdict.KrdictEntry, item_id: str, roman: str, sense_number: int) -> dict:
    sense = next(s for s in entry.senses if s.number == sense_number)
    gloss = {"en": sense.en}
    if sense.id:
        gloss["id"] = sense.id
    return {
        "id": item_id,
        "type": "word",
        "text": entry.word,
        "roman": roman,
        "gloss": gloss,
        "source": krdict.SOURCE,
        "license": krdict.LICENSE,
        "source_ref": f"{krdict.SOURCE}:{entry.target_code}#{sense.number}",
        "review": "needs_review",
    }


def apply_overrides(
    course_dir: Path,
    rels: list[str],
    units: list[dict],
    ovs: list[overrides.Override],
    by_code: dict[int, krdict.KrdictEntry],
    summary: Summary,
    dry_run: bool,
) -> None:
    """Apply overrides to existing items that still hold their generated krdict value.

    Reviewed items and hand-edited items (anything else) are left alone.
    """
    for rel, unit in zip(rels, units, strict=True):
        changed = False
        for n, item in enumerate(unit["items"]):
            o = overrides.find(ovs, item)
            if not o:
                continue
            plain = _regenerate(item, by_code)
            target = overrides.apply(o, plain) if plain else None
            if item == target:
                continue
            if item["review"] == "reviewed" or item != plain:
                summary.kept.append(item["id"])
                continue
            unit["items"][n] = target
            summary.overridden.append(item["id"])
            changed = True
        if changed and not dry_run:
            dump_yaml(unit, course_dir / rel)


def _regenerate(item: dict, by_code: dict[int, krdict.KrdictEntry]) -> dict | None:
    """The item as `build` generated it from its krdict source_ref (None if not from krdict)."""
    code, _, sense = (
        str(item.get("source_ref", "")).removeprefix(f"{krdict.SOURCE}:").partition("#")
    )
    entry = by_code.get(int(code)) if code.isdigit() else None
    if not entry or not sense.isdigit() or int(sense) not in {s.number for s in entry.senses}:
        return None
    fresh = to_item(entry, item["id"], item["roman"], int(sense))
    return {**item, "gloss": fresh["gloss"], "source": fresh["source"]}


def _senses(entry: krdict.KrdictEntry) -> list[tuple[int, str, str | None]]:
    """The senses a word can be taught with: those with an English gloss."""
    return [(s.number, s.en, s.id) for s in entry.senses if s.en]


def _new_item(entry_roman: tuple, item_id: str, senses: dict, ovs: list) -> dict:
    entry, roman = entry_roman
    item = to_item(entry, item_id, roman, senses.get(item_id, entry.senses[0].number))
    o = overrides.find(ovs, item)
    return overrides.apply(o, item) if o else item


def assign_ids(pool: list, taken: set[str]) -> list[tuple[krdict.KrdictEntry, str, str]]:
    """(entry, id, roman). Homographs and clashes with existing IDs get a -<target_code> suffix."""
    out = []
    for entry in pool:
        roman = romanize(entry.word, entry.pronunciation)
        item_id = f"ko.w.{slugify(roman)}"
        if item_id in taken:
            item_id = f"{item_id}-{entry.target_code}"
        taken.add(item_id)
        out.append((entry, item_id, roman))
    return out


def build(
    course_id: str,
    n_units: int = 12,
    dry_run: bool = False,
    run: Callable[[str], str] = run_claude,
    courses: Path = COURSES,
    cache: Path = CACHE,
    source_zip: Path | None = None,
) -> Summary:
    if course_id != "ko-en":
        raise ValueError(f"build only supports ko-en for now, not {course_id}")
    course_dir = courses / course_id
    zip_path = source_zip or fetch.check("krdict")
    beginner, total = krdict.load_beginner(
        zip_path, cache / f"krdict-{fetch.sha256(zip_path)[:16]}.json"
    )
    candidates, stats = krdict.vocabulary_candidates(beginner)
    stats["total entries"] = total

    course_file = course_dir / "course.yaml"
    course = load_yaml(course_file)
    # Existing units are never regenerated, only new units are appended, so reviewed items and
    # manual edits stay safe. The one exception is overrides.yaml (see apply_overrides).
    # ponytail: krdict updates don't reach existing items; reuse _regenerate if that matters.
    existing = [load_yaml(course_dir / rel) for rel in course["units"]]
    items = [i for u in existing for i in u["items"]]
    used = {str(i.get("source_ref", "")).split("#")[0] for i in items}  # krdict:<target_code>
    taken = {i["id"] for i in items} | {u["id"] for u in existing}

    fresh = [e for e in candidates if f"{krdict.SOURCE}:{e.target_code}" not in used]
    core_file = course_dir / "core-words.yaml"
    core_words = load_yaml(core_file)["words"] if core_file.is_file() else []
    fresh_codes = {e.target_code for e in fresh}
    core = [e for e in core_entries(core_words, candidates) if e.target_code in fresh_codes]
    core_codes = {e.target_code for e in core}
    rest = [e for e in fresh if e.target_code not in core_codes]
    pool = core + select_pool(rest, POOL_SIZE - len(core))
    summary = Summary(stats=stats, pool=len(pool), existing_units=len(existing))
    ovs = overrides.load(course_dir)
    by_code = {e.target_code: e for e in beginner}
    apply_overrides(course_dir, course["units"], existing, ovs, by_code, summary, dry_run)
    missing = n_units - len(existing)
    if missing <= 0:
        return summary

    assigned = assign_ids(pool, taken)
    by_id = {item_id: (entry, roman) for entry, item_id, roman in assigned}
    prompt_rows = [
        {
            "id": i,
            "text": e.word,
            "pos": e.pos,
            "gloss": e.senses[0].en,
            "category": e.category,
        }
        for e, i, _ in assigned
    ]
    required = frozenset(i for e, i, _ in assigned if e.target_code in core_codes)
    titles = [u["title"]["en"] for u in existing]
    plans = group(prompt_rows, missing, titles, run, cache / "llm", required)

    titled = [
        {
            "title": plan.title_en,
            "words": [
                {"id": i, "text": by_id[i][0].word, "senses": _senses(by_id[i][0])}
                for i in plan.items
            ],
        }
        for plan in plans
    ]
    senses = pick_senses(titled, run, cache / "llm")

    numbers = [int(Path(rel).name[:3]) for rel in course["units"] if Path(rel).name[:3].isdigit()]
    number = max([FIRST_UNIT - 1, *numbers]) + 1
    for plan in plans:
        name = f"{number:03d}-{plan.slug}"
        unit = {
            "id": f"ko-{name}",
            "title": {"en": plan.title_en, "id": plan.title_id},
            "level": LEVEL,
            "items": [_new_item(by_id[i], i, senses, ovs) for i in plan.items],
        }
        rel = f"units/{name}.yaml"
        summary.new_units.append((rel, len(unit["items"])))
        if not dry_run:
            (course_dir / "units").mkdir(exist_ok=True)
            dump_yaml(unit, course_dir / rel)
            course["units"].append(rel)
        number += 1
    if not dry_run:
        dump_yaml(course, course_file)
    return summary

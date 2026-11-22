"""`pipeline build ko-en`: krdict → romanize → group (claude -p) → units/*.yaml + course.yaml."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path

import yaml

from pipeline import fetch
from pipeline.group import group, run_claude
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


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(data, path: Path) -> None:
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    path.write_text(text, encoding="utf-8")


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


def to_item(entry: krdict.KrdictEntry, item_id: str, roman: str) -> dict:
    sense = entry.senses[0]
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
        "source_ref": entry.source_ref,
        "review": "needs_review",
    }


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
    # ponytail: existing units are never rewritten, only new units are appended. That keeps reviewed
    # items and manual edits safe, but krdict updates don't reach existing items; add a snapshot
    # diff (regenerate only items still equal to their last generated value) if that matters.
    existing = [load_yaml(course_dir / rel) for rel in course["units"]]
    items = [i for u in existing for i in u["items"]]
    used_refs = {i.get("source_ref") for i in items}
    taken = {i["id"] for i in items} | {u["id"] for u in existing}

    pool = select_pool([e for e in candidates if e.source_ref not in used_refs])
    summary = Summary(stats=stats, pool=len(pool), existing_units=len(existing))
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
            "gloss": {"en": e.senses[0].en},
            "category": e.category,
        }
        for e, i, _ in assigned
    ]
    plans = group(prompt_rows, missing, [u["title"]["en"] for u in existing], run, cache / "llm")

    numbers = [int(Path(rel).name[:3]) for rel in course["units"] if Path(rel).name[:3].isdigit()]
    number = max([FIRST_UNIT - 1, *numbers]) + 1
    for plan in plans:
        name = f"{number:03d}-{plan.slug}"
        unit = {
            "id": f"ko-{name}",
            "title": {"en": plan.title_en, "id": plan.title_id},
            "level": LEVEL,
            "items": [to_item(by_id[i][0], i, by_id[i][1]) for i in plan.items],
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

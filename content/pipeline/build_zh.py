"""`pipeline build zh-en`: HSK 2.0 level → CC-CEDICT entries → group + pick senses + Indonesian
glosses (claude -p) → units/*.yaml.

The HSK list only decides which words go in a level (LICENSES.md decision 1). Text, pinyin and
English glosses come from CC-CEDICT verbatim; Indonesian glosses are translated by boso.
"""

import math
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ValidationError

from pipeline import fetch
from pipeline.build import CACHE, COURSES, FIRST_UNIT, Summary, dump_yaml, load_yaml
from pipeline.group import _ask, _json_object, _template, group, pick_senses, run_claude
from pipeline.importers import cedict, hsk
from pipeline.nlp.zh import roman, slug, tones

GROUP_TEMPLATE = "group-units-zh.v1"
SENSE_TEMPLATE = "pick-senses-zh.v1"
GLOSS_TEMPLATE = "translate-glosses-zh.v1"
UNIT_SIZE = 7  # words per unit on average (5–8 allowed)
BOSO = {"source": "boso", "license": "CC BY-SA 4.0"}
ERHUA = re.compile(r"^erhua variant of (?:\S+\|)?(\S+?)\[")

Sense = tuple[cedict.Entry, str]


class Glosses(BaseModel):
    glosses: dict[str, str]


def word_senses(word: str, by_simp: dict[str, list[cedict.Entry]]) -> list[Sense]:
    """What `word` can be taught as. An erhua entry (一点儿) borrows the senses of the word it is
    a variant of (一点), keeping its own pinyin."""
    out = cedict.senses(by_simp.get(word, []))
    for e in by_simp.get(word, []):
        for d in e.defs:
            if m := ERHUA.match(d):
                base = cedict.senses(by_simp.get(m[1], []))
                out += [
                    (cedict.Entry(e.trad, e.simp, e.pinyin, base[0][0].defs), x) for _, x in base
                ]
    return out


def assign_ids(words: list[tuple[str, list[Sense]]], taken: set[str]) -> dict[str, str]:
    """word → ID from the pinyin of its first sense; a clash (他/她/它 are all ta1) gets the
    hex code of the characters as a suffix."""
    out = {}
    for word, senses in words:
        item_id = f"zh.w.{slug(senses[0][0].pinyin)}"
        if item_id in taken:
            item_id += "-" + "".join(f"{ord(c):x}" for c in word)
        taken.add(item_id)
        out[word] = item_id
    return out


def parse_glosses(text: str, ids: set[str]) -> dict[str, str]:
    try:
        got = Glosses.model_validate_json(_json_object(text)).glosses
    except ValidationError as e:
        raise ValueError(str(e)) from e
    if set(got) != ids:
        raise ValueError(
            f"glosses don't match: missing {sorted(ids - set(got))}, extra {sorted(set(got) - ids)}"
        )
    if bad := [i for i, g in got.items() if not g.strip() or len(g) > 80]:
        raise ValueError(f"empty or longer than 80 characters: {bad}")
    return {i: g.strip() for i, g in got.items()}


def translate_glosses(items: list[dict], run: Callable[[str], str], cache_dir: Path):
    lines = [f"{i['id']} | {i['text']} | {i['roman']} | {i['gloss']['en']}" for i in items]
    prompt = _template(GLOSS_TEMPLATE).format(words="\n".join(lines))
    ids = {i["id"] for i in items}
    return _ask(GLOSS_TEMPLATE, prompt, lambda t: parse_glosses(t, ids), run, cache_dir)


def to_item(item_id: str, sense: Sense, gloss_id: str) -> dict:
    entry, definition = sense
    return {
        "id": item_id,
        "type": "word",
        "text": entry.simp,
        "roman": roman(entry.pinyin),
        "tones": tones(entry.pinyin),
        "gloss": {"en": cedict.clean(definition), "id": gloss_id},
        "gloss_sources": {"id": dict(BOSO)},
        "source": cedict.SOURCE,
        "license": cedict.LICENSE,
        "source_ref": entry.source_ref,
        "review": "needs_review",
    }


def build(
    course_id: str = "zh-en",
    level: int = 1,
    dry_run: bool = False,
    courses: Path = COURSES,
    run: Callable[[str], str] = run_claude,
    cache: Path = CACHE,
    sources: tuple[Path, dict[int, Path]] | None = None,
) -> Summary:
    """Add units for the HSK `level` words that no unit has yet. Existing units are never
    touched, so reviewed items and manual edits stay safe."""
    cedict_path, hsk_paths = sources or (
        fetch.check("cedict"),
        {n: fetch.check(fetch.hsk_key(n)) for n in fetch.HSK_LEVELS},
    )
    by_simp: dict[str, list[cedict.Entry]] = {}
    for e in cedict.load(cedict_path):
        by_simp.setdefault(e.simp, []).append(e)

    course_dir = courses / course_id
    course_file = course_dir / "course.yaml"
    course = load_yaml(course_file)
    existing = [load_yaml(course_dir / rel) for rel in course["units"]]
    items = [i for u in existing for i in u["items"]]
    used = {i["text"] for i in items}
    stats = Counter()
    words = []
    for w in hsk.words(hsk_paths[level]):
        senses = word_senses(w, by_simp)
        if w in used:
            stats["already in a unit"] += 1
        elif not senses:
            stats["not in CC-CEDICT"] += 1
        else:
            words.append((w, senses))
    summary = Summary(stats=stats, pool=len(words), existing_units=len(existing))
    if not words:
        return summary

    ids = assign_ids(words, {i["id"] for i in items})
    senses = {ids[w]: s for w, s in words}
    rows = [
        {"id": ids[w], "text": w, "pos": roman(s[0][0].pinyin), "gloss": s[0][1], "category": "-"}
        for w, s in words
    ]
    n_units = math.ceil(len(words) / UNIT_SIZE)
    titles = [u["title"]["en"] for u in existing]
    plans = group(rows, n_units, titles, run, cache / "llm", frozenset(senses), GROUP_TEMPLATE)

    titled = [
        {
            "title": plan.title_en,
            "words": [
                {
                    "id": i,
                    "text": senses[i][0][0].simp,
                    "senses": [
                        (n, f"{roman(e.pinyin)}: {d}", None)
                        for n, (e, d) in enumerate(senses[i], 1)
                    ],
                }
                for i in plan.items
            ],
        }
        for plan in plans
    ]
    picks = pick_senses(titled, run, cache / "llm", SENSE_TEMPLATE)
    chosen = {i: s[picks.get(i, 1) - 1] for i, s in senses.items()}
    draft = [to_item(i, chosen[i], "") for i in chosen]
    id_glosses = translate_glosses(draft, run, cache / "llm")

    numbers = [int(Path(r).name[:3]) for r in course["units"] if Path(r).name[:3].isdigit()]
    number = max([FIRST_UNIT - 1, *numbers]) + 1
    for plan in plans:
        name = f"{number:03d}-{plan.slug}"
        unit = {
            "id": f"zh-{name}",
            "title": {"en": plan.title_en, "id": plan.title_id},
            "level": f"hsk{level}",
            "items": [to_item(i, chosen[i], id_glosses[i]) for i in plan.items],
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

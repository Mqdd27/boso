"""`pipeline pinyin <course>`: the pinyin + tones script units (001–009) from
courses/<course>/pinyin.yaml.

Hand-written content (source: boso), no external data, no LLM, deterministic. Like `hangul`, it
only adds: an existing unit file is never rewritten (it is reported as kept when it differs).
readings.yaml gets the character TTS reads for each syllable (existing entries win).
"""

from pathlib import Path

from pipeline.build import dump_yaml, load_yaml
from pipeline.hangul import LICENSE, SOURCE, Summary
from pipeline.nlp.zh import mark, slug

LEVEL = "hsk1"


def item(numbered: str, en: str, id_: str) -> dict:
    return {
        "id": f"zh.c.{slug(numbered)}",
        "type": "char",
        "text": mark(numbered),
        "roman": mark(numbered),
        "tones": numbered,
        "gloss": {"en": en, "id": id_},
        "source": SOURCE,
        "license": LICENSE,
        "review": "needs_review",
    }


def units(spec: dict) -> list[tuple[str, dict]]:
    out = []
    for u in spec["units"]:
        name = f"{u['number']:03d}-{u['slug']}"
        unit = {
            "id": f"zh-{name}",
            "title": u["title"],
            "level": LEVEL,
            "kind": "script",
            "items": [item(n, en, id_) for n, _, en, id_ in u["items"]],
        }
        out.append((f"units/{name}.yaml", unit))
    return out


def generate(course_dir: Path, dry_run: bool = False) -> Summary:
    spec = load_yaml(course_dir / "pinyin.yaml")
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

    course_file = course_dir / "course.yaml"
    course = load_yaml(course_file)
    script = [rel for rel, _ in generated]
    ordered = script + [rel for rel in course["units"] if rel not in script]

    readings_file = course_dir / "readings.yaml"
    readings = (load_yaml(readings_file) or {}) if readings_file.is_file() else {}
    for u in spec["units"]:
        for numbered, hanzi, _, _ in u["items"]:
            key = f"zh.c.{slug(numbered)}"
            if key not in readings:
                readings[key] = hanzi
                summary.readings += 1
    if not dry_run:
        if ordered != course["units"]:
            course["units"] = ordered
            dump_yaml(course, course_file)
        if summary.readings:
            dump_yaml(dict(sorted(readings.items())), readings_file)
    return summary

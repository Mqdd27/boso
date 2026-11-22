"""`pipeline pack <course>`: validate, then write dist/<course>/ (JSON + audio/)."""

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from pipeline import tts
from pipeline.overrides import SUFFIX
from pipeline.validate import ROOT, check, cross_check, validate_course_dir

CONTENT = ROOT / "content"
DIST = CONTENT / "dist"
ATTRIBUTION = CONTENT / "ATTRIBUTION.md"

# Credit lines for each `source` value used in courses/.
SOURCES = {
    "krdict": {
        "name": "한국어기초사전 (Basic Korean Dictionary)",
        "author": "국립국어원 (National Institute of Korean Language)",
        "url": "https://krdict.korean.go.kr",
    },
    "tatoeba": {
        "name": "Tatoeba",
        "url": "https://tatoeba.org",
    },
    "boso": {
        "name": "boso (written or translated for this course)",
        "author": "boso contributors",
        "url": "https://github.com/Mqdd27/boso",
    },
}


def _build_date() -> str:
    """UTC now, or SOURCE_DATE_EPOCH for reproducible builds."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    now = datetime.fromtimestamp(int(epoch), UTC) if epoch else datetime.now(UTC)
    return now.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def attribution(units: list[dict]) -> list[dict]:
    """One entry per (source, license): how many items use it and who wrote them.

    A sentence can credit several sources: its own (the Korean text) and one per gloss language
    in `gloss_sources` (a Tatoeba translation by another author, or a boso translation)."""
    items: dict[tuple[str, str], set[str]] = {}
    authors: dict[tuple[str, str], set[str]] = {}
    for u in units:
        for x in [*u["items"], *u.get("grammar", [])]:
            credits = [x, *x.get("gloss_sources", {}).values()] if "source" in x else []
            for c in credits:
                key = (c["source"], c["license"])
                items.setdefault(key, set()).add(x["id"])
                if "author" in c:
                    authors.setdefault(key, set()).add(c["author"])
    out = []
    for (source, license_), ids in sorted(items.items()):
        entry = {"source": source, "license": license_, "items": len(ids)}
        info = SOURCES.get(source.removesuffix(SUFFIX), {})
        if "url" in info:
            entry["url"] = info["url"]
        if names := authors.get((source, license_)):
            entry["authors"] = sorted(names)
        elif "author" in info:
            entry["authors"] = [info["author"]]
        out.append(entry)
    return out


def load_course(course_dir: Path) -> dict:
    """The pack form of a course: course.yaml meta with units inlined. Raises on invalid input."""
    errors, units = validate_course_dir(course_dir)
    if errors:
        raise ValueError("\n".join(errors))
    meta = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    return {**{k: v for k, v in meta.items() if k != "units"}, "units": units}


def add_audio(course: dict, course_dir: Path, out: Path, cache: Path) -> int:
    """Copy generated audio (cache/tts/) into out/audio/ and set `item.audio`, only for items
    whose file exists. Returns how many items got audio."""
    audio_dir = out / "audio"
    shutil.rmtree(audio_dir, ignore_errors=True)  # no stale files from renamed or removed items
    lang = course["target"]
    if lang not in tts.VOICES:
        return 0
    read = tts.readings(course_dir)
    n = 0
    for unit in course["units"]:
        for item in unit["items"]:
            src = cache / f"{tts.cache_key(read.get(item['id'], item['text']), lang)}.opus"
            if not src.is_file():
                continue
            rel = tts.audio_path(item["id"])
            (audio_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, audio_dir / rel)
            item["audio"] = rel
            n += 1
    return n


def pack(
    course_id: str,
    courses: Path = CONTENT / "courses",
    dist: Path = DIST,
    tts_cache: Path = tts.CACHE,
) -> tuple[Path, int, int]:
    """Write the pack. Returns (output dir, items with audio, items)."""
    course = load_course(courses / course_id)
    out = dist / course_id
    out.mkdir(parents=True, exist_ok=True)
    audio = add_audio(course, courses / course_id, out, tts_cache)
    meta = {k: v for k, v in course.items() if k != "units"}
    manifest = {
        "schema_version": 1,
        "course": meta,
        "build_date": _build_date(),
        "attribution": attribution(course["units"]),
    }
    errors = check(course, "course", "course.json") + check(manifest, "manifest", "manifest.json")
    errors += cross_check(course, course["units"], "course.json")
    if errors:
        raise ValueError("\n".join(errors))
    for name, data in [("course.json", course), ("manifest.json", manifest)]:
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        (out / name).write_text(text, encoding="utf-8")
    return out, audio, sum(len(u["items"]) for u in course["units"])


def write_attribution(courses: Path = CONTENT / "courses", path: Path = ATTRIBUTION) -> None:
    """ATTRIBUTION.md for every course, from the same item metadata as the manifests."""
    lines = [
        "# Attribution",
        "",
        "Generated by `pipeline pack` from the `source` / `license` of every item. Do not edit.",
        "",
    ]
    for course_file in sorted(courses.glob("*/course.yaml")):
        course = load_course(course_file.parent)
        entries = attribution(course["units"])
        lines += [f"## {course['id']}", ""]
        if not entries:
            lines += ["No third-party content yet.", ""]
        for e in entries:
            info = SOURCES.get(e["source"].removesuffix(SUFFIX), {})
            name = info.get("name", e["source"])
            credit = f"[{name}]({info['url']})" if info else name
            by = f" by {', '.join(e['authors'])}" if e.get("authors") else ""
            line = f"- {credit}{by}, {e['license']}: {e['items']} items"
            if e["source"].endswith(SUFFIX):
                line += (
                    f", glosses modified by boso (see courses/{course['id']}/overrides.yaml"
                    " for what changed and why)"
                )
            lines.append(line)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

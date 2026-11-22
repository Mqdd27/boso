"""`pipeline lint <course>`: cheap gloss checks, no LLM. Reports only; never edits or reviews.

Suggestions come from krdict: other senses of the same entry, then same-word 초급 entries.
Without the krdict dump (e.g. in CI) the checks still run, just without suggestions.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeline import fetch
from pipeline.importers import krdict
from pipeline.validate import validate_course_dir

# Indonesian multipliers that need a count in front ("sepuluh ribu", not "puluh ribu").
BARE_MULTIPLIER = re.compile(r"^(puluh|ratus|ribu|juta)\b")
TRUNCATED = re.compile(r"([,;:/(\-]|\b(atau|dan|yang|or|and|the|of))\s*$")
ENTITY = re.compile(r"&[a-z]+;?|&#\d+;?")


@dataclass
class Finding:
    unit: str
    item: str
    problem: str
    suggestion: str = ""


def gloss_problems(lang: str, text: str | None) -> list[str]:
    """What looks wrong with one gloss string."""
    if not text or not text.strip():
        return [f"{lang} gloss is empty"]
    problems = []
    first = re.split(r"[,;]", text)[0].strip()
    if lang == "id" and BARE_MULTIPLIER.match(first):
        problems.append(
            f"id gloss {text!r} starts with a bare multiplier (sepuluh/seratus/seribu?)"
        )
    if TRUNCATED.search(text) or text.count("(") != text.count(")"):
        problems.append(f"{lang} gloss {text!r} looks cut off")
    if ENTITY.search(text):
        problems.append(f"{lang} gloss {text!r} has an HTML entity")
    return problems


def _target_code(item: dict) -> int | None:
    m = re.fullmatch(r"krdict:(\d+)#\d+", item.get("source_ref", ""))
    return int(m[1]) if m else None


def _suggest(
    item: dict, entries: dict[int, krdict.KrdictEntry], by_word: dict, lang: str, avoid: str = ""
) -> str:
    """The first krdict sense (same entry first, then same word) with a clean `lang` gloss that
    differs from `avoid`."""
    code = _target_code(item)
    current = item.get("source_ref")
    pool = ([entries[code]] if code in entries else []) + [
        e for e in by_word.get(item["text"], []) if e.target_code != code
    ]
    for entry in pool:
        for sense in entry.senses:
            ref = f"krdict:{entry.target_code}#{sense.number}"
            gloss = getattr(sense, lang)
            clean = sense.en and not gloss_problems(lang, gloss)
            if ref != current and clean and gloss.strip().lower() != avoid:
                return f"{ref}: en {sense.en!r}, id {sense.id!r}"
    return ""


def load_entries(source_zip: Path | None, cache: Path) -> list[krdict.KrdictEntry]:
    """초급 krdict entries, or [] when the dump isn't available."""
    try:
        zip_path = source_zip or fetch.check("krdict")
    except RuntimeError:
        return []
    beginner, _ = krdict.load_beginner(
        zip_path, cache / f"krdict-{fetch.sha256(zip_path)[:16]}.json"
    )
    return beginner


def lint(course_dir: Path, entries: list[krdict.KrdictEntry]) -> list[Finding]:
    errors, units = validate_course_dir(course_dir)
    if errors:
        raise ValueError("\n".join(errors))
    by_code = {e.target_code: e for e in entries}
    by_word: dict[str, list] = {}
    for e in entries:
        by_word.setdefault(e.word, []).append(e)

    findings = []
    for unit in units:
        seen: dict[tuple[str, str], str] = {}
        for item in unit["items"]:
            gloss = item.get("gloss", {})
            for lang in ("en", "id"):
                for problem in gloss_problems(lang, gloss.get(lang)):
                    suggestion = _suggest(item, by_code, by_word, lang)
                    findings.append(Finding(unit["id"], item["id"], problem, suggestion))
                text = (gloss.get(lang) or "").strip().lower()
                if not text:
                    continue
                if (lang, text) in seen:
                    findings.append(
                        Finding(
                            unit["id"],
                            item["id"],
                            f"same {lang} gloss {gloss[lang]!r} as {seen[lang, text]}",
                            _suggest(item, by_code, by_word, lang, avoid=text),
                        )
                    )
                else:
                    seen[lang, text] = item["id"]

    core_file = course_dir / "core-words.yaml"
    if core_file.is_file():
        items = [i for u in units for i in u["items"]]
        for spec in yaml.safe_load(core_file.read_text(encoding="utf-8"))["words"]:
            word, _, code = str(spec).partition("#")
            if not any(
                (i["text"] == word and (not code or _target_code(i) == int(code))) for i in items
            ):
                findings.append(Finding("-", "-", f"core word {spec!r} is not in any unit"))
    return findings

"""Group candidate words into themed units with the Claude Code CLI (build time only)."""

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

CONTENT = Path(__file__).resolve().parents[1]
TEMPLATE = CONTENT / "prompts" / "group-units.v1.md"
TEMPLATE_VERSION = "group-units.v1"
LLM_CACHE = CONTENT / "cache" / "llm"


class UnitPlan(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=40)
    title_en: str = Field(min_length=1)
    title_id: str = Field(min_length=1)
    items: list[str] = Field(min_length=5, max_length=8)


class Plan(BaseModel):
    units: list[UnitPlan]


def run_claude(prompt: str) -> str:
    """Call `claude -p` headless and return the model's text reply."""
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout)
    # Older CLIs print one result object, newer ones the whole event list.
    events = out if isinstance(out, list) else [out]
    result = next(e for e in reversed(events) if e.get("type") == "result")
    if result.get("is_error"):
        raise RuntimeError(f"claude -p failed: {result.get('result')}")
    return result["result"]


def render(candidates: list[dict], n_units: int, existing_titles: list[str]) -> str:
    lines = [
        f"{c['id']} | {c['text']} | {c['pos']} | {c['gloss']['en']} | {c['category'] or '-'}"
        for c in candidates
    ]
    return TEMPLATE.read_text(encoding="utf-8").format(
        n_units=n_units,
        existing_titles=", ".join(existing_titles) or "(none)",
        candidates="\n".join(lines),
    )


def parse_plan(text: str, pool: set[str], n_units: int) -> list[UnitPlan]:
    """Validate the LLM reply. Raises ValueError on anything off."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in reply")
    try:
        plan = Plan.model_validate_json(text[start : end + 1])
    except ValidationError as e:
        raise ValueError(str(e)) from e
    if len(plan.units) != n_units:
        raise ValueError(f"expected {n_units} units, got {len(plan.units)}")
    seen: set[str] = set()
    slugs: set[str] = set()
    for unit in plan.units:
        if unit.slug in slugs:
            raise ValueError(f"duplicate unit slug {unit.slug}")
        slugs.add(unit.slug)
        for item in unit.items:
            if item not in pool:
                raise ValueError(f"unknown id {item}")
            if item in seen:
                raise ValueError(f"id {item} used twice")
            seen.add(item)
    return plan.units


def group(
    candidates: list[dict],
    n_units: int,
    existing_titles: list[str],
    run: Callable[[str], str] = run_claude,
    cache_dir: Path = LLM_CACHE,
) -> list[UnitPlan]:
    """Plan `n_units` units from `candidates`. Cached by hash(template version + prompt)."""
    prompt = render(candidates, n_units, existing_titles)
    key = hashlib.sha256(f"{TEMPLATE_VERSION}\n{prompt}".encode()).hexdigest()
    cached = cache_dir / f"{key}.json"
    pool = {c["id"] for c in candidates}
    if cached.is_file():
        return parse_plan(cached.read_text(encoding="utf-8"), pool, n_units)
    error = None
    for _ in range(2):  # one retry, then fail loudly
        reply = run(prompt)
        try:
            units = parse_plan(reply, pool, n_units)
        except ValueError as e:
            error = e
            continue
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(Plan(units=units).model_dump_json(indent=2), encoding="utf-8")
        return units
    raise RuntimeError(f"Claude returned an invalid unit plan twice: {error}")

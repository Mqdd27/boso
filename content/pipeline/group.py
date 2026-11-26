"""LLM steps of the build, via the Claude Code CLI (build time only).

- `group`: themed units from a pool of candidate word IDs.
- `pick_senses`: for words with several krdict senses, the sense that fits the unit's theme.

The LLM only picks from what it is given (IDs, sense numbers); every reply is validated, retried
once, then the build fails. Replies are cached by hash(template version + prompt).
"""

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

CONTENT = Path(__file__).resolve().parents[1]
PROMPTS = CONTENT / "prompts"
LLM_CACHE = CONTENT / "cache" / "llm"
GROUP_TEMPLATE = "group-units.v2"
SENSE_TEMPLATE = "pick-senses.v1"
MAX_SENSES = 8  # senses shown per word; the first ones are the common ones


class UnitPlan(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=40)
    title_en: str = Field(min_length=1)
    title_id: str = Field(min_length=1)
    items: list[str] = Field(min_length=5, max_length=8)


class Plan(BaseModel):
    units: list[UnitPlan]


class SensePicks(BaseModel):
    senses: dict[str, int]


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


def _json_object(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in reply")
    return text[start : end + 1]


def _ask[T](
    template: str,
    prompt: str,
    parse: Callable[[str], T],
    run: Callable[[str], str],
    cache_dir: Path,
) -> T:
    key = hashlib.sha256(f"{template}\n{prompt}".encode()).hexdigest()
    cached = cache_dir / f"{key}.json"
    if cached.is_file():
        return parse(cached.read_text(encoding="utf-8"))
    error = None
    for attempt in range(2):  # one retry that names the problem, then fail loudly
        retry = (
            f"\n\nYour previous reply was invalid: {error}\nReply again, fixed." if attempt else ""
        )
        reply = run(prompt + retry)
        try:
            result = parse(reply)
        except ValueError as e:
            error = e
            continue
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(_json_object(reply) + "\n", encoding="utf-8")
        return result
    raise RuntimeError(f"Claude returned an invalid reply for {template} twice: {error}")


def _template(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def parse_plan(
    text: str, pool: set[str], n_units: int, required: frozenset[str] = frozenset()
) -> list[UnitPlan]:
    """Validate a unit plan. Raises ValueError on anything off."""
    try:
        plan = Plan.model_validate_json(_json_object(text))
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
    if missing := sorted(required - seen):
        raise ValueError(f"core words missing from every unit: {', '.join(missing)}")
    return plan.units


def group(
    candidates: list[dict],
    n_units: int,
    existing_titles: list[str],
    run: Callable[[str], str] = run_claude,
    cache_dir: Path = LLM_CACHE,
    required: frozenset[str] = frozenset(),
    template: str = GROUP_TEMPLATE,
) -> list[UnitPlan]:
    """Plan `n_units` units from `candidates` ({id, text, pos, gloss, category}).

    Every ID in `required` (the core words) must end up in a unit."""
    words = {c["id"]: c["text"] for c in candidates}
    lines = [
        f"{c['id']} | {c['text']} | {c['pos']} | {c['gloss']} | {c['category'] or '-'}"
        for c in candidates
    ]
    prompt = _template(template).format(
        n_units=n_units,
        existing_titles=", ".join(existing_titles) or "(none)",
        required=", ".join(f"{i} ({words[i]})" for i in sorted(required)) or "(none)",
        candidates="\n".join(lines),
    )
    pool = {c["id"] for c in candidates}
    parse = lambda t: parse_plan(t, pool, n_units, required)  # noqa: E731
    return _ask(template, prompt, parse, run, cache_dir)


def parse_senses(text: str, choices: dict[str, set[int]]) -> dict[str, int]:
    """Validate sense picks: exactly the asked IDs, each with one of its offered numbers."""
    try:
        picks = SensePicks.model_validate_json(_json_object(text)).senses
    except ValidationError as e:
        raise ValueError(str(e)) from e
    if set(picks) != set(choices):
        missing, extra = sorted(set(choices) - set(picks)), sorted(set(picks) - set(choices))
        raise ValueError(f"sense picks don't match: missing {missing}, extra {extra}")
    for item_id, number in picks.items():
        if number not in choices[item_id]:
            raise ValueError(f"sense {number} is not offered for {item_id}")
    return picks


def pick_senses(
    units: list[dict],
    run: Callable[[str], str] = run_claude,
    cache_dir: Path = LLM_CACHE,
    template: str = SENSE_TEMPLATE,
) -> dict[str, int]:
    """{item id: sense number} for every word with more than one sense offered.

    `units` is [{title, words: [{id, text, senses: [(number, en, id), ...]}]}]. Words with a
    single sense are not asked about.
    """
    blocks, choices = [], {}
    for unit in units:
        lines = []
        for w in unit["words"]:
            senses = w["senses"][:MAX_SENSES]
            if len(senses) < 2:
                continue
            choices[w["id"]] = {n for n, _, _ in senses}
            options = "; ".join(f"{n}: {en}" + (f" ({i})" if i else "") for n, en, i in senses)
            lines.append(f"  {w['id']} | {w['text']} | {options}")
        if lines:
            blocks.append(f"Unit: {unit['title']}\n" + "\n".join(lines))
    if not choices:
        return {}
    prompt = _template(template).format(units="\n\n".join(blocks))
    return _ask(template, prompt, lambda t: parse_senses(t, choices), run, cache_dir)

"""Gloss overrides (`courses/<course>/overrides.yaml`) for source glosses that are wrong.

An overridden item gets `source: "<source> (modified)"` (CC BY-SA: changes must be indicated).
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SUFFIX = " (modified)"


class Override(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str = Field(min_length=1)  # item id, or `text#krdict target_code`
    gloss: dict[Literal["en", "id"], str] = Field(min_length=1)
    reason: str = Field(min_length=1)


def load(course_dir: Path) -> list[Override]:
    path = course_dir / "overrides.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [Override.model_validate(o) for o in data.get("overrides") or []]


def matches(o: Override, item: dict) -> bool:
    if o.item == item["id"]:
        return True
    text, _, code = o.item.partition("#")
    ref = str(item.get("source_ref", ""))
    return bool(code) and item["text"] == text and ref.split("#")[0].endswith(f":{code}")


def find(overrides: list[Override], item: dict) -> Override | None:
    return next((o for o in overrides if matches(o, item)), None)


def base_source(item: dict) -> str:
    return item["source"].removesuffix(SUFFIX)


def apply(o: Override, item: dict) -> dict:
    return {
        **item,
        "gloss": {**item["gloss"], **o.gloss},
        "source": base_source(item) + SUFFIX,
    }


def check(course_dir: Path, units: list[dict]) -> list[str]:
    """Errors for a malformed overrides.yaml or overrides that match no item."""
    path = course_dir / "overrides.yaml"
    try:
        overrides = load(course_dir)
    except (ValidationError, yaml.YAMLError) as e:
        return [f"{path}: {e}"]
    items = [i for u in units for i in u["items"]]
    return [
        f"{path}: override {o.item!r} matches no item in any unit"
        for o in overrides
        if not any(matches(o, i) for i in items)
    ]

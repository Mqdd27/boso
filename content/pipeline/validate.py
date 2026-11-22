"""Validate course YAML and pack JSON against schema/course-pack.schema.json."""

import json
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]  # repo root
SCHEMA_PATH = ROOT / "schema" / "course-pack.schema.json"


@cache
def _validator(definition: str) -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return Draft202012Validator({"$ref": f"{schema['$id']}#/$defs/{definition}"}, registry=registry)


def check(data: Any, definition: str, label: str) -> list[str]:
    """Schema errors for `data` against `$defs/<definition>`, prefixed with `label`."""
    errors = sorted(_validator(definition).iter_errors(data), key=lambda e: list(e.absolute_path))
    return [f"{label}: /{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in errors]


def cross_check(course: dict, units: list[dict], label: str) -> list[str]:
    """Rules JSON Schema can't express: levels exist, IDs unique, IDs match the target."""
    errors = []
    target, levels, seen = course["target"], set(course["levels"]), set()
    for unit in units:
        ids = [unit["id"]] + [i["id"] for i in unit["items"]]
        ids += [g["id"] for g in unit.get("grammar", [])]
        if unit["level"] not in levels:
            errors.append(f"{label}: unit {unit['id']}: level {unit['level']!r} not in {levels}")
        for id_ in ids:
            if not id_.startswith((f"{target}-", f"{target}.")):
                errors.append(f"{label}: {id_}: does not belong to target {target!r}")
            if id_ in seen:
                errors.append(f"{label}: {id_}: duplicate id")
            seen.add(id_)
    return errors


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_course_dir(course_dir: Path) -> tuple[list[str], list[dict]]:
    """Validate course.yaml plus every unit it lists. Returns (errors, valid units)."""
    course_file = course_dir / "course.yaml"
    course = _load_yaml(course_file)
    errors = check(course, "courseSource", str(course_file))
    if errors:
        return errors, []
    units = []
    for rel in course["units"]:
        path = course_dir / rel
        if not path.is_file():
            errors.append(f"{course_file}: unit file {rel} not found")
            continue
        unit = _load_yaml(path)
        unit_errors = check(unit, "unit", str(path))
        errors += unit_errors
        if not unit_errors:
            units.append(unit)
    listed = {(course_dir / rel).resolve() for rel in course["units"]}
    for path in sorted(course_dir.glob("units/**/*.yaml")):
        if path.resolve() not in listed:
            errors.append(f"{path}: not listed in {course_file}")
    errors += cross_check(course, units, str(course_file))
    return errors, units


def validate_pack_file(path: Path) -> list[str]:
    """Validate a pack JSON file: *.course.json or *manifest.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if path.name.endswith("manifest.json"):
        return check(data, "manifest", str(path))
    errors = check(data, "course", str(path))
    return errors or cross_check(data, data["units"], str(path))


def validate_all(root: Path = ROOT) -> tuple[list[str], dict[str, int]]:
    """Validate content/courses/*/ and schema/examples/*.json under repo `root`."""
    errors: list[str] = []
    stats = {"courses": 0, "units": 0, "items": 0, "examples": 0}
    for course_file in sorted(root.glob("content/courses/*/course.yaml")):
        course_errors, units = validate_course_dir(course_file.parent)
        errors += course_errors
        stats["courses"] += 1
        stats["units"] += len(units)
        stats["items"] += sum(len(u["items"]) for u in units)
    for path in sorted((root / "schema" / "examples").glob("*.json")):
        errors += validate_pack_file(path)
        stats["examples"] += 1
    return errors, stats

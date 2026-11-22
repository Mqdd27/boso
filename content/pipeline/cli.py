"""`pipeline` command line."""

import argparse
import sys
from pathlib import Path

from pipeline.validate import ROOT, validate_all


def cmd_validate(args: argparse.Namespace) -> int:
    errors, stats = validate_all(args.root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s)", file=sys.stderr)
        return 1
    print("ok: " + ", ".join(f"{v} {k}" for k, v in stats.items()))
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    from pipeline import fetch

    path = fetch.fetch_krdict(args.src)
    print(f"krdict: {path} ({fetch.read_lock()['krdict']['sha256']})")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from pipeline.build import build

    summary = build(args.course, n_units=args.units, dry_run=args.dry_run)
    for key, value in sorted(summary.stats.items()):
        print(f"{key}: {value}")
    print(f"pool: {summary.pool}, existing units: {summary.existing_units}")
    prefix = "would write" if args.dry_run else "wrote"
    for rel, n in summary.new_units:
        print(f"{prefix} {rel} ({n} words)")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    from pipeline.pack import pack, write_attribution

    out = pack(args.course)
    write_attribution()
    print(f"wrote {out}/course.json, {out}/manifest.json and ATTRIBUTION.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline", description="boso course-pack pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="schema-check content/courses/ and schema/examples/")
    validate.add_argument("--root", type=Path, default=ROOT, help="repo root (default: this repo)")
    validate.set_defaults(func=cmd_validate)
    fetch = sub.add_parser("fetch", help="download a source into sources/ and pin it")
    fetch.add_argument("source", choices=["krdict"])
    fetch.add_argument("--from", dest="src", type=Path, help="use a manually downloaded file")
    fetch.set_defaults(func=cmd_fetch)
    build = sub.add_parser("build", help="generate new units into courses/<course>/")
    build.add_argument("course", choices=["ko-en"])
    build.add_argument("--units", type=int, default=12, help="total vocab units wanted")
    build.add_argument("--dry-run", action="store_true", help="print, don't write")
    build.set_defaults(func=cmd_build)
    pack = sub.add_parser("pack", help="write dist/<course>/course.json + manifest.json")
    pack.add_argument("course")
    pack.set_defaults(func=cmd_pack)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

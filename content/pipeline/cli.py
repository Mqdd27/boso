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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline", description="boso course-pack pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="schema-check content/courses/ and schema/examples/")
    validate.add_argument("--root", type=Path, default=ROOT, help="repo root (default: this repo)")
    validate.set_defaults(func=cmd_validate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

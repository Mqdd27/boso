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

    if args.source == "tatoeba":
        for path in fetch.fetch_tatoeba(force=args.force):
            print(f"tatoeba: {path.name} ({path.stat().st_size // 1024} KB)")
        return 0
    path = fetch.fetch_krdict(args.src)
    print(f"krdict: {path} ({fetch.read_lock()['krdict']['sha256']})")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from pipeline.build import build

    summary = build(args.course, n_units=args.units, dry_run=args.dry_run)
    for key, value in sorted(summary.stats.items()):
        print(f"{key}: {value}")
    print(f"pool: {summary.pool}, existing units: {summary.existing_units}")
    for item_id in summary.overridden:
        print(f"{'would apply' if args.dry_run else 'applied'} override to {item_id}")
    for item_id in summary.kept:
        print(f"kept {item_id}: reviewed or edited by hand, override not applied")
    prefix = "would write" if args.dry_run else "wrote"
    for rel, n in summary.new_units:
        print(f"{prefix} {rel} ({n} words)")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    from pipeline.pack import pack, write_attribution

    out, audio, items = pack(args.course)
    write_attribution()
    print(f"wrote {out}/course.json, {out}/manifest.json and ATTRIBUTION.md")
    print(f"audio: {audio}/{items} items")
    if audio < items:
        print(f"warning: {items - audio} item(s) without audio (run `pipeline tts {args.course}`)")
    return 0


def cmd_hangul(args: argparse.Namespace) -> int:
    from pipeline.build import COURSES
    from pipeline.hangul import generate

    summary = generate(COURSES / args.course, dry_run=args.dry_run)
    prefix = "would write" if args.dry_run else "wrote"
    for rel in summary.written:
        print(f"{prefix} {rel}")
    for rel in summary.kept:
        print(f"kept {rel}: differs from hangul.yaml (edited by hand?), not rewritten")
    print(f"{len(summary.unchanged)} unit(s) unchanged, {summary.readings} new reading(s)")
    return 0


def cmd_sentences(args: argparse.Namespace) -> int:
    from pipeline.sentences import generate

    s = generate(
        args.course,
        max_unknown=args.max_unknown,
        min_known_ratio=args.min_known_ratio,
        max_eojeol=args.max_eojeol,
        per_unit=args.per_unit,
        dry_run=args.dry_run,
    )
    for key, value in s.sources.items():
        print(f"{key}: {value}")
    print("placed per vocab unit (tatoeba/krdict), by --max-unknown:")
    for n, per_unit in sorted(s.coverage.items()):
        cells = " ".join(f"{c['tatoeba']}/{c['krdict']}" for c in per_unit)
        print(f"  {n}: {cells}  (units with none: {sum(not c for c in per_unit)})")
    verb = "would add" if args.dry_run else "added"
    for rel, ids in s.added.items():
        print(f"{verb} {len(ids)} to {rel}: {', '.join(ids)}")
    if not args.dry_run:
        print(f"translations from claude -p: {s.translated}")
    return 0


def cmd_tts(args: argparse.Namespace) -> int:
    from pipeline import tts
    from pipeline.build import COURSES

    try:
        tts.check_tools()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    report = tts.generate(args.course, COURSES, sample=args.sample, only=args.only)
    size = sum(f.stat().st_size for f in report.files)
    print(
        f"{len(report.files)} files ({len(report.made)} new, {report.cached} cached), "
        f"{size / 1024:.0f} KB, {report.seconds:.0f}s"
    )
    if args.sample:
        print(f"samples: {tts.SAMPLES}  (listen: open {tts.SAMPLES})")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    from pipeline.build import CACHE, COURSES
    from pipeline.lint import lint, load_entries

    entries = load_entries(None, CACHE)
    if not entries:
        print("note: krdict dump not found, no suggestions (run `pipeline fetch krdict`)")
    findings = lint(COURSES / args.course, entries)
    for f in findings:
        line = f"warning: {f.unit} | {f.item} | {f.problem}"
        print(line + (f" | try {f.suggestion}" if f.suggestion else ""))
    print(f"{len(findings)} warning(s)")
    return 1 if args.strict and findings else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline", description="boso course-pack pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="schema-check content/courses/ and schema/examples/")
    validate.add_argument("--root", type=Path, default=ROOT, help="repo root (default: this repo)")
    validate.set_defaults(func=cmd_validate)
    fetch = sub.add_parser("fetch", help="download a source into sources/ and pin it")
    fetch.add_argument("source", choices=["krdict", "tatoeba"])
    fetch.add_argument("--force", action="store_true", help="download again (tatoeba)")
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
    hangul = sub.add_parser("hangul", help="write the Hangul script units from hangul.yaml")
    hangul.add_argument("course", choices=["ko-en"])
    hangul.add_argument("--dry-run", action="store_true", help="print, don't write")
    hangul.set_defaults(func=cmd_hangul)
    sentences = sub.add_parser("sentences", help="add Tatoeba + krdict sentences to vocab units")
    sentences.add_argument("course", choices=["ko-en"])
    sentences.add_argument("--max-unknown", type=int, default=1, help="new content words allowed")
    sentences.add_argument("--min-known-ratio", type=float, default=0.9)
    sentences.add_argument("--max-eojeol", type=int, default=8, help="longest sentence, in words")
    sentences.add_argument("--per-unit", type=int, default=6, help="sentences per unit at most")
    sentences.add_argument("--dry-run", action="store_true", help="print, don't translate or write")
    sentences.set_defaults(func=cmd_sentences)
    tts = sub.add_parser("tts", help="generate missing audio (MeloTTS env in content/tts/)")
    tts.add_argument("course", choices=["ko-en"])
    tts.add_argument("--sample", type=int, metavar="N", help="only the first N items, to listen to")
    tts.add_argument("--only", metavar="ID", help="regenerate one item")
    tts.set_defaults(func=cmd_tts)
    lint = sub.add_parser("lint", help="warn about suspicious glosses (no LLM, no edits)")
    lint.add_argument("course")
    lint.add_argument("--strict", action="store_true", help="exit 1 if there are warnings")
    lint.set_defaults(func=cmd_lint)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

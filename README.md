# boso-content

Course content and build pipeline for **boso**, an open-source, self-hostable, Duolingo-style
language learning app. The pipeline turns openly licensed dictionaries and sentence corpora into
versioned course packs (`<course>.course.zip`: JSON + audio) that the app imports.

First courses: Korean (`ko-en`) and Mandarin (`zh-en`).

## Layout

```
schema/     course-pack JSON Schema (source of truth; the app copies it) + examples
courses/    human-editable YAML per course (course.yaml + units/*.yaml)
pipeline/   Python package with the `pipeline` CLI
tests/      pytest
LICENSES.md license check of every data source and tool
```

## License

This repo uses two licenses:

| Path | License |
|---|---|
| Course content: `courses/`, generated course packs | [CC BY-SA 4.0](LICENSE) |
| Code and schema: `pipeline/`, `schema/`, `tests/`, build/CI files | [Unlicense](UNLICENSE) (public domain) |

Content is CC BY-SA because its sources (krdict, CC-CEDICT, Tatoeba) are CC BY / CC BY-SA, and
share-alike content can't be relicensed. Every item keeps its `source`, `license` and `author`, and
packs carry an attribution list. See [LICENSES.md](LICENSES.md) for each source.

## Setup

Needs [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed).

```bash
uv sync
```

## Commands

```bash
uv run pipeline validate    # schema-check courses/**/*.yaml and schema/examples/
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Course pack format

`schema/course-pack.schema.json` (JSON Schema draft 2020-12) defines:

- `courseSource`: `courses/<id>/course.yaml`, units listed as file paths
- `unit`: `courses/<id>/units/*.yaml`
- `course`: `course.json` inside a pack, units inlined
- `manifest`: `manifest.json` inside a pack (course meta, schema version, build date, attribution)

Item IDs are stable (`ko.w.<slug>`, `zh.s.<slug>`, `ko.g.<slug>`, …) and are never renumbered,
because learner progress is keyed on them.

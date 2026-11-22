# boso content

Course content and the build pipeline for boso. The pipeline turns openly licensed dictionaries and
sentence corpora into versioned course packs (`<course>.course.zip`: JSON + audio) that the app imports.

First courses: Korean (`ko-en`) and Mandarin (`zh-en`).

## Layout

```
courses/     human-editable YAML per course (course.yaml + units/*.yaml), CC BY-SA 4.0
pipeline/    Python package with the `pipeline` CLI
tests/       pytest
LICENSES.md  license check of every data source and tool
../schema/   course-pack JSON Schema (shared with the app) + examples
```

## License

- `courses/` and generated course packs: [CC BY-SA 4.0](courses/LICENSE). The sources (krdict,
  CC-CEDICT, Tatoeba) are CC BY / CC BY-SA, and share-alike content can't be relicensed.
- Everything else here (`pipeline/`, `tests/`, config): [Unlicense](../LICENSE), like the rest of the repo.

Every item keeps its `source`, `license` and `author`, and packs carry an attribution list.
See [LICENSES.md](LICENSES.md) for each source.

## Setup and commands

Needs [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed). Run from `content/`:

```bash
uv sync
uv run pipeline validate    # schema-check courses/**/*.yaml and ../schema/examples/
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Course pack format

`../schema/course-pack.schema.json` (JSON Schema draft 2020-12) defines:

- `courseSource`: `courses/<id>/course.yaml`, units listed as file paths
- `unit`: `courses/<id>/units/*.yaml`
- `course`: `course.json` inside a pack, units inlined
- `manifest`: `manifest.json` inside a pack (course meta, schema version, build date, attribution)

Item IDs are stable (`ko.w.<slug>`, `zh.s.<slug>`, `ko.g.<slug>`, …) and are never renumbered,
because learner progress is keyed on them.

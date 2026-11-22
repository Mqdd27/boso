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

## Building the Korean course (ko-en)

```bash
uv run pipeline fetch krdict          # download the full krdict JSON dump into sources/
uv run pipeline build ko-en           # add vocab units to courses/ko-en/ (default: up to 12 units)
uv run pipeline build ko-en --dry-run # show what would be written
uv run pipeline pack ko-en            # validate + write dist/ko-en/{course,manifest}.json, ATTRIBUTION.md
```

- **krdict dump:** `fetch` downloads 한국어기초사전's "사전 전체 내려받기" (JSON, ~85 MB zip, no key
  needed) and pins its sha256 in `sources.lock`. If the download fails, get it by hand from
  https://krdict.korean.go.kr (footer → 사전 전체 내려받기 → Json) and run
  `uv run pipeline fetch krdict --from <file.zip>`. `build` refuses a dump that doesn't match the lock.
  The dump already has English and Indonesian equivalents, so no `KRDICT_API_KEY` is needed.
- **Words:** 초급 (TOPIK I) single words with an English equivalent; affixes, particles, auxiliary
  verbs and phrases are dropped. `en` / `id` glosses are krdict's equivalents for the first sense,
  `roman` is Revised Romanization from krdict's pronunciation.
- **Units:** a deterministic pool of 250 words is grouped into themed units of 5–8 words by
  `claude -p` (Claude Code CLI) with `prompts/group-units.v1.md`. The pool starts with
  `courses/ko-en/core-words.yaml` (greetings, numbers, family: edit it to add must-have words) and
  is filled up from krdict's semantic categories, most senses first.
- **Senses:** for words with several krdict senses, `claude -p` picks the one that fits the unit
  (`prompts/pick-senses.v1.md`: 시키다 in a food unit → "order (food)"). It only picks a sense
  number; the gloss text is still krdict's.
- Every Claude reply is validated (only offered IDs / sense numbers), retried once, and cached in
  `cache/llm/`, so rebuilds don't call Claude again.
- **Review status:** generated items are `review: needs_review`. That is metadata, not a gate: they
  are used in lessons normally. Only fluent contributors set `review: reviewed`, via PR (see
  [CONTRIBUTING.md](../CONTRIBUTING.md)); the pipeline never does.
- **Lint:** `uv run pipeline lint ko-en` warns about empty glosses, cut-off or odd number glosses
  ("puluh ribu"), identical glosses within a unit, and core words missing from every unit, with
  other krdict senses as suggestions. It never edits files. `--strict` exits 1 on warnings.
- **Merging:** `build` only appends new units. Existing unit files, reviewed items and manual edits
  are never rewritten, and words already in the course are not offered again.

## Course pack format

`../schema/course-pack.schema.json` (JSON Schema draft 2020-12) defines:

- `courseSource`: `courses/<id>/course.yaml`, units listed as file paths
- `unit`: `courses/<id>/units/*.yaml`
- `course`: `course.json` inside a pack, units inlined
- `manifest`: `manifest.json` inside a pack (course meta, schema version, build date, attribution)

Item IDs are stable (`ko.w.<slug>`, `zh.s.<slug>`, `ko.g.<slug>`, …) and are never renumbered,
because learner progress is keyed on them.

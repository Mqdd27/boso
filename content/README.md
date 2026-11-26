# boso content

Course content and the build pipeline for boso. The pipeline turns openly licensed dictionaries and
sentence corpora into versioned course packs (`<course>.course.zip`: JSON + audio) that the app imports.

First courses: Korean (`ko-en`) and Mandarin (`zh-en`).

## Layout

```
courses/     human-editable YAML per course (course.yaml + units/*.yaml), CC BY-SA 4.0
pipeline/    Python package with the `pipeline` CLI
tts/         separate MeloTTS env (Python 3.10, torch) used by `pipeline tts`
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
- **Core words must land in a unit:** the grouping reply is rejected if a core word is missing;
  Claude gets one retry that names the missing words, then the build fails.
- **Overrides:** `courses/ko-en/overrides.yaml` fixes krdict glosses that are wrong (e.g. 만 =
  "puluh ribu" → "sepuluh ribu"). Each entry names an item (id or `text#target_code`), the new
  `en`/`id` gloss and a one-sentence reason. `build` applies it to items that still hold their
  generated value (never to reviewed or hand-edited items) and sets `source: krdict (modified)`;
  `ATTRIBUTION.md` notes the change, as CC BY-SA requires. `validate` fails on an override that
  matches no item. Its `hints` list fixes a sentence hint that took the wrong krdict sense (e.g.
  빼면 = "take out" → sense 2 "subtract"): a `token`, a krdict `word#target_code/sense` and a
  reason. The gloss is krdict's own text, so it isn't marked modified.
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

### Sentences

```bash
uv run pipeline fetch tatoeba          # Tatoeba exports (Korean + their en/id translations, ~44 MB)
uv run pipeline sentences ko-en --dry-run   # coverage per unit, nothing written
uv run pipeline sentences ko-en        # append sentences to the vocab units
```

- **Sources:** Tatoeba Korean sentences (with their author; orphans, sentences tagged `@…` or
  `non-sentence`, and their translations likewise are dropped; Tatoeba audio is never used) and
  the 문장 examples of krdict's 초급 entries. Korean text is never written by an LLM.
- **Placement:** [Kiwi](https://github.com/bab2min/kiwipiepy) splits each sentence into morphemes.
  A sentence goes into the earliest vocab unit where at most `--max-unknown` (1) content words
  (nouns, verbs and adjectives as `-다` lemmas, adverbs, numerals, determiners) are not taught yet,
  and at least `--min-known-ratio` (0.9) of all morphemes are known (particles and endings count as
  known). Words are matched with their word class, so 일 "one" is not 일 "work". Sentences with
  Latin letters, hanja or digits are skipped, as are one-word ones and ones over `--max-eojeol`.
  Hangul units get none.
- **Choice:** at most `--per-unit` (6) per unit: sentences using the unit's own words first, then
  ones with a human English translation, then the shortest. One sentence per set of content words
  and per English gloss in a unit (밥 먹었어? / 밥 먹었어요? are one).
- **Translations:** Tatoeba's own `eng` / `ind` translations when linked (with their author).
  Missing ones (all krdict examples, almost every Indonesian gloss) come from `claude -p`
  (`prompts/translate-sentences.v1.md`), validated and cached like the other LLM steps, and are
  credited to boso in `gloss_sources`.
- **Hints:** words of a sentence that are not taught yet get krdict's gloss in `hints` (shown on
  tap in the app).
- **Merging:** sentences are only appended to units; existing items are never changed, and
  sentences close to one already in the unit are not added.

## Audio (MeloTTS)

Audio is generated once on the maintainer's machine and shipped in the pack; the app and the server
never run TTS. MeloTTS needs torch and old pins, so it lives in its own env (`tts/`), not in the
pipeline's dependencies (CI never installs it).

```bash
brew install ffmpeg
tts/setup.sh                          # one time: uv sync in tts/, unidic + model download (~2 GB)
uv run pipeline tts ko-en --sample 5  # first 5 items → cache/tts-sample/<id>.opus, listen first
uv run pipeline tts ko-en             # everything missing (cached: re-runs only make new items)
uv run pipeline tts ko-en --only ko.w.ne  # remake one item
uv run pipeline pack ko-en            # copies audio into dist/ko-en/audio/ and sets item.audio
```

- Voice: MeloTTS-Korean, speaker `KR`, speed 0.9. Then ffmpeg trims silence, normalises loudness to
  -16 LUFS and encodes mono Opus at 32 kbps (~3–6 KB per word).
- Files are cached in `cache/tts/` by hash of the text read and every setting, so changing a
  setting only remakes the files it affects.
- `courses/<course>/readings.yaml` (optional, `item id: text`) sets what is read aloud when it
  differs from `text`, e.g. a Hangul letter ㄱ read as 기역.
- `item.audio` is a build artefact: it is set in the pack only, never written into `courses/`.
  `pack` without generated audio still works (warning); the app then uses the browser's voice.

### Mandarin (zh-en)

```bash
uv run pipeline fetch cedict && uv run pipeline fetch hsk   # CC-CEDICT + HSK 2.0 word lists
uv run pipeline pinyin zh-en           # pinyin + tones units 001–009 from pinyin.yaml
uv run pipeline build zh-en --level 1  # HSK1 vocab units (claude -p groups, picks senses, ID glosses)
uv run pipeline sentences zh-en        # Tatoeba Mandarin sentences (jieba words, pypinyin)
uv run pipeline tts zh-en && uv run pipeline pack zh-en
```

- Voice: MeloTTS-Chinese (`ZH`), +20 dB before trimming (it comes out much quieter than Korean).
- MeloTTS says single syllables with unreliable tones, so every single-syllable item (pinyin units,
  one-character words) gets its pitch redrawn to the textbook tone shape with WORLD (pyworld) in
  `tts/synth.py`. Neutral-tone syllables keep MeloTTS's pitch.

## Course pack format

`../schema/course-pack.schema.json` (JSON Schema draft 2020-12) defines:

- `courseSource`: `courses/<id>/course.yaml`, units listed as file paths
- `unit`: `courses/<id>/units/*.yaml`
- `course`: `course.json` inside a pack, units inlined
- `manifest`: `manifest.json` inside a pack (course meta, schema version, build date, attribution)

Item IDs are stable (`ko.w.<slug>`, `zh.s.<slug>`, `ko.g.<slug>`, …) and are never renumbered,
because learner progress is keyed on them.

# Contributing

## Reviewing content (fluent speakers)

Course items carry a `review` field. `needs_review` is normal: those items are used in lessons like
any other. Review marks an item as checked by a fluent speaker; it never gates anything.

- **Who:** native or fluent speakers of the target language (Korean for `ko-en`, Mandarin for
  `zh-en`). The maintainer, agents and the pipeline never set `review: reviewed`.
- **How:** open `content/courses/<course>/units/*.yaml` and check each item's `gloss`. If a gloss is
  wrong, fix it, preferably with another sense from the same source (krdict: update `gloss` and the
  sense number in `source_ref`). Then set `review: reviewed`.
- `uv run pipeline lint <course>` (in `content/`) lists glosses that look off, with suggestions.
- **PRs:** one PR per unit. Say which sources you used to check (e.g. krdict, Naver dictionary).
- The pipeline never overwrites `reviewed` items or manual edits: `pipeline build` only appends new
  units.

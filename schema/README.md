# schema

`course-pack.schema.json` (JSON Schema draft 2020-12) is the single source of truth for course packs.
It is used by:

- the content pipeline (`content/`), to validate course YAML before building packs
- the app (`apps/web`, `apps/server`), to validate packs on load and reject packs that don't match

`examples/` holds small, made-up packs that must always validate (checked in CI).

Changing the schema affects both sides: bump `manifest.schema_version` for breaking changes and update
the examples in the same commit.

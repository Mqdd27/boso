# boso

Open-source, self-hostable language learning app with a structured path:
script → vocabulary → phrases → sentences → grammar, plus spaced-repetition review (FSRS).
First courses: Korean and Mandarin. UI in English and Indonesian.

"Boso" is Javanese for "language".

**Status: pre-alpha.** Only the scaffolding exists so far. There are no lessons yet.

## Goals

- One Docker container, no GPU, no API keys, no external services, no analytics.
- Works offline as a PWA. An account is optional and only used for sync.
- Course content comes from openly licensed sources and keeps its attribution.

## Repo layout

```
apps/web/      SvelteKit (static SPA) + TypeScript + Tailwind, i18n with Paraglide
apps/server/   Go single binary: API + serves the built web app
schema/        course-pack JSON Schema (shared by the app and the content pipeline)
content/       course content (YAML) + Python build pipeline, see content/README.md
```

## Development

Needs Node 24+, Go 1.27+, and (for `content/`) [uv](https://docs.astral.sh/uv/).

```bash
npm install
npm run dev      # web dev server + Go server (data in ./.data)
npm run lint     # prettier, eslint, svelte-check, go vet, gofmt
npm test         # vitest + go test
npm run build    # build the web app, then the Go binary with the web app embedded
```

End-to-end smoke test (Playwright):

```bash
cd apps/web
npx playwright install chromium
npm run test:e2e
```

## Self-hosting

```bash
docker build -t boso .
docker run -p 8080:8080 -v boso-data:/data boso
```

Then open http://localhost:8080. Health check: `GET /healthz` returns `{"status":"ok"}`.

Configuration is via environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `BOSO_ADDR` | `:8080` | listen address |
| `BOSO_DATA_DIR` | `/data` | persistent data (`boso.db`, `courses/`) |

## License

- Code (everything outside `content/courses/`): [Unlicense](LICENSE), public domain.
- Course content (`content/courses/`) and generated course packs: [CC BY-SA 4.0](content/courses/LICENSE),
  because the sources it is built from (krdict, CC-CEDICT, Tatoeba) are CC BY / CC BY-SA.
  See [content/LICENSES.md](content/LICENSES.md).

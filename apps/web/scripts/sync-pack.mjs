// Copy built course packs into static/packs/ (git-ignored) so the app can fetch them.
//   node scripts/sync-pack.mjs            content/dist/<course>/ → static/packs/<course>/
//   node scripts/sync-pack.mjs --fixture  testdata/packs/<course>/ (CI, e2e: no Python needed)
//   PACKS_URL=<.tar.gz of <course>/ folders> node scripts/sync-pack.mjs
//     downloads the packs instead, e.g. the `packs` GitHub release (`npm run publish-packs`), for
//     hosts that build from git without the Python pipeline (Vercel).
// A missing pack is a warning, not an error: the app then shows its "no course yet" screen.
import { execFileSync } from 'node:child_process';
import {
	cpSync,
	existsSync,
	mkdirSync,
	mkdtempSync,
	readdirSync,
	rmSync,
	writeFileSync
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const fixture = process.argv.includes('--fixture');
const url = !fixture && process.env.PACKS_URL;
const src = fixture
	? join(web, 'testdata/packs')
	: url
		? await download(url)
		: join(web, '../../content/dist');

/** @param {string} url */
async function download(url) {
	const res = await fetch(url);
	if (!res.ok) throw new Error(`sync-pack: ${url}: HTTP ${res.status}`);
	const tmp = mkdtempSync(join(tmpdir(), 'boso-packs-'));
	writeFileSync(join(tmp, 'packs.tar.gz'), Buffer.from(await res.arrayBuffer()));
	mkdirSync(join(tmp, 'packs'));
	execFileSync('tar', ['-xzf', join(tmp, 'packs.tar.gz'), '-C', join(tmp, 'packs')]);
	return join(tmp, 'packs');
}
const out = join(web, 'static/packs');

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

const courses = [];
for (const course of existsSync(src) ? readdirSync(src) : []) {
	const files = ['course.json', 'manifest.json'];
	if (!files.every((f) => existsSync(join(src, course, f)))) continue;
	mkdirSync(join(out, course));
	for (const f of files) cpSync(join(src, course, f), join(out, course, f));
	const audio = join(src, course, 'audio');
	if (existsSync(audio)) cpSync(audio, join(out, course, 'audio'), { recursive: true });
	courses.push(course);
}
courses.sort();
writeFileSync(join(out, 'index.json'), JSON.stringify({ courses }) + '\n');

if (courses.length) console.log(`sync-pack: ${courses.join(', ')} from ${url || src}`);
else if (url) throw new Error(`sync-pack: no course pack in ${url}`);
else
	console.warn(
		`sync-pack: no course pack in ${src}. Build one with: cd content && uv run pipeline pack ko-en`
	);

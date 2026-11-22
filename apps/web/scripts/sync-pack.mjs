// Copy built course packs into static/packs/ (git-ignored) so the app can fetch them.
//   node scripts/sync-pack.mjs            content/dist/<course>/ → static/packs/<course>/
//   node scripts/sync-pack.mjs --fixture  testdata/packs/<course>/ (CI, e2e: no Python needed)
// A missing pack is a warning, not an error: the app then shows its "no course yet" screen.
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const fixture = process.argv.includes('--fixture');
const src = fixture ? join(web, 'testdata/packs') : join(web, '../../content/dist');
const out = join(web, 'static/packs');

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

const courses = [];
for (const course of existsSync(src) ? readdirSync(src) : []) {
	const files = ['course.json', 'manifest.json'];
	if (!files.every((f) => existsSync(join(src, course, f)))) continue;
	mkdirSync(join(out, course));
	for (const f of files) cpSync(join(src, course, f), join(out, course, f));
	courses.push(course);
}
courses.sort();
writeFileSync(join(out, 'index.json'), JSON.stringify({ courses }) + '\n');

if (courses.length) console.log(`sync-pack: ${courses.join(', ')} from ${src}`);
else
	console.warn(
		`sync-pack: no course pack in ${src}. Build one with: cd content && uv run pipeline pack ko-en`
	);

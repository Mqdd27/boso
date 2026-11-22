import { describe, expect, it } from 'vitest';
import course from '../../testdata/packs/ko-en/course.json';
import manifest from '../../testdata/packs/ko-en/manifest.json';
import { listCourses, loadPack, PackError, validatePack } from './pack.js';

const clone = <T>(x: T): T => structuredClone(x);

describe('pack validation', () => {
	it('accepts the fixture pack', () => {
		expect(validatePack(clone(course), clone(manifest)).course.units).toHaveLength(5);
	});

	const broken: [string, (c: typeof course, m: typeof manifest) => void, RegExp][] = [
		['missing gloss', (c) => delete (c.units[0].items[0] as { gloss?: unknown }).gloss, /gloss/],
		['bad item id', (c) => (c.units[0].items[0].id = 'Bad Id'), /pattern/],
		['no units', (c) => (c.units = []), /fewer than 1/],
		[
			'bad schema_version',
			(_, m) => ((m as { schema_version: number }).schema_version = 2),
			/manifest/
		],
		[
			'unknown unit kind',
			(c) => ((c.units[2] as { kind: string }).kind = 'lesson'),
			/kind|allowed/
		],
		['char item without a ko.c. id', (c) => (c.units[0].items[0].type = 'char'), /pattern/],
		['duplicate id', (c) => (c.units[1].items[0].id = c.units[0].items[0].id), /duplicate/]
	];
	it('accepts an old unit without kind', () => {
		const c = clone(course);
		delete (c.units[2] as { kind?: string }).kind;
		expect(() => validatePack(c, clone(manifest))).not.toThrow();
	});

	for (const [name, mutate, message] of broken) {
		it(`rejects a pack with ${name}`, () => {
			const c = clone(course);
			const m = clone(manifest);
			mutate(c, m);
			expect(() => validatePack(c, m)).toThrow(PackError);
			expect(() => validatePack(c, m)).toThrow(message);
		});
	}
});

describe('loading', () => {
	const fake =
		(files: Record<string, unknown>): typeof fetch =>
		(url) => {
			const key = url as string;
			return Promise.resolve(
				key in files ? new Response(JSON.stringify(files[key])) : new Response('', { status: 404 })
			);
		};

	it('lists synced courses, or none', async () => {
		expect(await listCourses(fake({ '/packs/index.json': { courses: ['ko-en'] } }))).toEqual([
			'ko-en'
		]);
		expect(await listCourses(fake({}))).toEqual([]);
	});

	it('rejects an invalid pack as a whole', async () => {
		const bad = clone(course);
		bad.units = [];
		const files = { '/packs/xx/course.json': bad, '/packs/xx/manifest.json': manifest };
		await expect(loadPack('xx', fake(files))).rejects.toThrow(PackError);
	});
});

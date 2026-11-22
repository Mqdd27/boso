import { describe, expect, it } from 'vitest';
import pack from '../../testdata/packs/ko-en/course.json';
import { distractors, generateLesson, LESSON_SIZE, lessonXp, requeue, rng } from './lesson.js';
import { compose, decompose } from './hangul.js';
import { gloss, type Course, type GlossLang } from './types.js';

const course = pack as Course;
const [greetings, family, vowels, consonants, blocks] = course.units;
const base = {
	earlier: [greetings],
	stats: {},
	seed: 42,
	lang: 'id' as GlossLang,
	canListen: true
};

describe('generateLesson', () => {
	it('is deterministic for a seed', () => {
		const a = generateLesson({ ...base, unit: family, lesson: 1 });
		expect(generateLesson({ ...base, unit: family, lesson: 1 })).toEqual(a);
		expect(generateLesson({ ...base, unit: family, lesson: 1, seed: 7 })).not.toEqual(a);
	});

	for (const lesson of [1, 2] as const) {
		for (const lang of ['en', 'id'] as GlossLang[]) {
			it(`lesson ${lesson} (${lang}): answer always offered, no duplicate glosses or texts`, () => {
				for (let seed = 0; seed < 50; seed++) {
					const exercises = generateLesson({ ...base, unit: family, lesson, seed, lang });
					const graded = exercises.filter((e) => e.kind !== 'intro');
					expect(graded.length).toBe(LESSON_SIZE);
					for (const e of exercises) {
						if (e.kind === 'intro' || e.kind === 'build') continue;
						const items = e.kind === 'match' ? e.items : e.options;
						if (e.kind !== 'match') expect(items.map((o) => o.id)).toContain(e.item.id);
						expect(new Set(items.map((o) => gloss(o, lang))).size).toBe(items.length);
						expect(new Set(items.map((o) => o.text)).size).toBe(items.length);
					}
				}
			});
		}
	}

	it('누나 and 언니 (same id gloss) are never options for each other', () => {
		const nuna = family.items.find((i) => i.text === '누나')!;
		const pool = [...family.items, ...greetings.items];
		for (let seed = 0; seed < 100; seed++) {
			expect(
				distractors(nuna, pool, (i) => gloss(i, 'id'), rng(seed)).map((i) => i.text)
			).not.toContain('언니');
		}
		// In English they differ ("elder sister" / "older sister"), so 언니 may appear.
		const seen = new Set<string>();
		for (let seed = 0; seed < 100; seed++) {
			for (const i of distractors(nuna, pool, (i) => gloss(i, 'en'), rng(seed))) seen.add(i.text);
		}
		expect(seen).toContain('언니');
	});

	it('introduces new words once, before their first exercise', () => {
		const exercises = generateLesson({ ...base, unit: greetings, earlier: [], lesson: 1 });
		const intros = exercises.filter((e) => e.kind === 'intro').map((e) => e.item.id);
		expect(intros.sort()).toEqual(greetings.items.map((i) => i.id).sort());
		const seen = Object.fromEntries(
			greetings.items.map((i) => [i.id, { id: i.id, seen: 1, correct: 1, wrong: 0, lastSeen: '' }])
		);
		const again = generateLesson({ ...base, unit: greetings, earlier: [], lesson: 1, stats: seen });
		expect(again.some((e) => e.kind === 'intro')).toBe(false);
	});

	it('lesson 2 starts with the words that were missed most', () => {
		const stats = {
			'ko.w.dongsaeng': { id: 'ko.w.dongsaeng', seen: 3, correct: 0, wrong: 3, lastSeen: '' }
		};
		const all = family.items.map((i) => ({
			id: i.id,
			seen: 1,
			correct: 1,
			wrong: 0,
			lastSeen: ''
		}));
		const lesson = generateLesson({
			...base,
			unit: family,
			lesson: 2,
			stats: { ...Object.fromEntries(all.map((s) => [s.id, s])), ...stats }
		});
		const first = lesson.find((e) => e.kind !== 'intro' && e.kind !== 'match');
		expect(first && 'item' in first && first.item.id).toBe('ko.w.dongsaeng');
	});

	it('without a Korean voice there are no listening exercises', () => {
		const lesson = generateLesson({ ...base, unit: family, lesson: 1, canListen: false });
		expect(lesson.some((e) => e.kind === 'listen')).toBe(false);
	});
});

describe('requeue + xp', () => {
	it('repeats a missed exercise at the end', () => {
		const queue = generateLesson({ ...base, unit: family, lesson: 1 });
		const again = requeue(queue, 3);
		expect(again.length).toBe(queue.length + 1);
		expect(again.at(-1)).toBe(queue[3]);
	});

	it('gives 10 XP, 15 without mistakes', () => {
		expect(lessonXp(0)).toBe(15);
		expect(lessonXp(2)).toBe(10);
	});
});

describe('script units', () => {
	const script = { ...base, earlier: [vowels, consonants], unit: blocks };
	const graded = (seed: number, lesson: 1 | 2 = 1) =>
		generateLesson({ ...script, seed, lesson }).filter((e) => e.kind !== 'intro');

	it('is deterministic for a seed', () => {
		expect(graded(3)).toEqual(graded(3));
		expect(graded(3)).not.toEqual(graded(4));
	});

	it('never offers two options with the same sound, nor vocab words', () => {
		for (let seed = 0; seed < 50; seed++) {
			for (const lesson of [1, 2] as const) {
				for (const e of graded(seed, lesson)) {
					if (e.kind === 'build') continue;
					const items = e.kind === 'match' ? e.items : e.options;
					expect(new Set(items.map((o) => o.roman)).size).toBe(items.length);
					expect(items.every((o) => o.type === 'char')).toBe(true);
				}
			}
		}
	});

	it('builds every block from tiles that contain its parts', () => {
		const builds = graded(1).filter((e) => e.kind === 'build');
		expect(builds.length).toBeGreaterThanOrEqual(blocks.items.length);
		for (const e of builds) {
			const parts = decompose(e.item.text)!;
			expect(e.tiles.initial).toContain(parts.initial);
			expect(e.tiles.vowel).toContain(parts.vowel);
			expect(e.tiles.final).toEqual([]);
			expect(compose(parts.initial, parts.vowel)).toBe(e.item.text);
		}
	});

	it('asks vowels among vowels in a letter unit', () => {
		const lesson = generateLesson({ ...script, earlier: [], unit: vowels, lesson: 1 });
		for (const e of lesson) {
			if (e.kind === 'meaning' || e.kind === 'word' || e.kind === 'listen')
				expect(e.options.every((o) => vowels.items.includes(o))).toBe(true);
		}
	});

	it('vocab lessons never offer Hangul letters', () => {
		const lesson = generateLesson({
			...base,
			earlier: [greetings, vowels],
			unit: family,
			lesson: 1
		});
		for (const e of lesson)
			if ('options' in e) expect(e.options.every((o) => o.type !== 'char')).toBe(true);
	});
});

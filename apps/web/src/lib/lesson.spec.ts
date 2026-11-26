import { describe, expect, it } from 'vitest';
import pack from '../../testdata/packs/ko-en/course.json';
import {
	arrangedRight,
	asksSound,
	cardRoman,
	distractors,
	generateLesson,
	LESSON_SIZE,
	lessonXp,
	requeue,
	rng
} from './lesson.js';
import { compose, decompose } from './hangul.js';
import { gloss, type Course, type GlossLang, type Item, type Unit } from './types.js';

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
						if (
							e.kind === 'intro' ||
							e.kind === 'build' ||
							e.kind === 'arrange' ||
							e.kind === 'tone'
						)
							continue;
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
		const words = greetings.items.filter((i) => i.type === 'word');
		expect(intros.sort()).toEqual(words.map((i) => i.id).sort());
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
					if (e.kind === 'build' || e.kind === 'arrange' || e.kind === 'tone') continue;
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

describe('sentences', () => {
	const sentences = greetings.items.filter((i) => i.type === 'sentence');
	const lesson2 = (seed: number, lesson: 1 | 2 = 2) =>
		generateLesson({ ...base, earlier: [], unit: greetings, lesson, seed });

	it('come only in lesson 2, at the end, deterministically, within the lesson size', () => {
		expect(lesson2(1, 1).some((e) => 'item' in e && e.item.type === 'sentence')).toBe(false);
		for (let seed = 0; seed < 30; seed++) {
			const graded = lesson2(seed).filter((e) => e.kind !== 'intro');
			expect(graded).toHaveLength(LESSON_SIZE);
			const tail = graded.slice(-sentences.length);
			expect(tail.every((e) => e.kind !== 'match' && e.item.type === 'sentence')).toBe(true);
			expect(lesson2(seed)).toEqual(lesson2(seed));
		}
	});

	it('word banks hold every card of the sentence plus decoys it does not use', () => {
		for (let seed = 0; seed < 30; seed++) {
			for (const e of lesson2(seed)) {
				if (e.kind !== 'arrange') continue;
				const own = e.item.tokens!;
				expect(e.bank.filter((t) => own.includes(t)).length).toBe(own.length);
				expect(e.bank.length - own.length).toBeLessThanOrEqual(2);
				expect(arrangedRight(own, e.item)).toBe(true);
			}
		}
	});

	it('word-bank cards carry their romanization', () => {
		const banks = Array.from({ length: 30 }, (_, seed) => lesson2(seed))
			.flat()
			.filter((e) => e.kind === 'arrange');
		expect(banks.length).toBeGreaterThan(0);
		for (const e of banks) {
			if (e.kind !== 'arrange') continue;
			expect(e.roman).toHaveLength(e.bank.length);
			expect(e.roman.every(Boolean)).toBe(true);
		}
		expect(cardRoman(sentences.find((s) => s.text === '친구야, 미안해.')!)).toEqual(
			new Map([
				['친구야', 'chinguya'],
				['미안해', 'mianhae']
			])
		);
	});

	it('introduce a new (hinted) word before a word bank that uses it, unless seen', () => {
		for (let seed = 0; seed < 30; seed++) {
			const lesson = lesson2(seed);
			lesson.forEach((e, n) => {
				if (e.kind !== 'arrange') return;
				for (const h of e.item.hints ?? []) {
					const intro = lesson
						.slice(0, n)
						.find((x) => x.kind === 'intro' && x.item.text === h.token);
					expect(intro && 'item' in intro && intro.item.gloss).toEqual(h.gloss);
				}
			});
			const seen = Object.fromEntries(
				sentences.map((s) => [s.id, { id: s.id, seen: 1, correct: 1, wrong: 0, lastSeen: '' }])
			);
			const again = generateLesson({
				...base,
				stats: seen,
				earlier: [],
				unit: greetings,
				lesson: 2,
				seed
			});
			expect(again.some((e) => e.kind === 'intro' && e.item.id.includes('.hint.'))).toBe(false);
		}
	});

	it('meaning options are sentences with different glosses', () => {
		const meanings = Array.from({ length: 30 }, (_, seed) => lesson2(seed))
			.flat()
			.filter((e) => e.kind === 'meaning' && e.item.type === 'sentence');
		expect(meanings.length).toBeGreaterThan(0);
		for (const e of meanings) {
			if (e.kind !== 'meaning') continue;
			expect(e.options.every((o) => o.type === 'sentence')).toBe(true);
			expect(new Set(e.options.map((o) => o.gloss.en)).size).toBe(e.options.length);
		}
	});

	it('checks a word-bank answer by its text, so duplicate cards can go either way', () => {
		const item = { ...sentences[0], tokens: ['네', '네', '고마워요'] };
		expect(arrangedRight(['네', '네', '고마워요'], item)).toBe(true);
		expect(arrangedRight(['네', '고마워요', '네'], item)).toBe(false);
		expect(arrangedRight(['네', '고마워요'], item)).toBe(false);
		expect(arrangedRight(['네', '네', '고마워요', '친구'], item)).toBe(false);
	});
});

describe('pinyin units', () => {
	const syl = (tones: string, text: string, en: string): Item => ({
		id: `zh.c.${tones}`,
		type: 'char',
		text,
		roman: text,
		tones,
		gloss: { en },
		source: 'boso',
		license: 'CC BY-SA 4.0',
		review: 'needs_review'
	});
	const tones: Unit = {
		id: 'zh-001-four-tones',
		title: { en: 'Tones' },
		level: 'hsk1',
		kind: 'script',
		items: [
			syl('ma1', 'mā', 'tone 1'),
			syl('ma2', 'má', 'tone 2'),
			syl('ma3', 'mǎ', 'tone 3'),
			syl('ma4', 'mà', 'tone 4'),
			syl('ma5', 'ma', 'neutral')
		]
	};
	const lesson = (canListen: boolean) =>
		generateLesson({ ...base, earlier: [], unit: tones, lesson: 1, canListen });

	it('ask for the meaning of a syllable, not its (visible) sound', () => {
		expect(asksSound(tones)).toBe(false);
		expect(asksSound(vowels)).toBe(true);
	});

	it('ask for the tone of each new syllable when it can be heard', () => {
		const picks = lesson(true).filter((e) => e.kind === 'tone');
		expect(new Set(picks.map((e) => e.item.id)).size).toBe(5);
		expect(lesson(false).some((e) => e.kind === 'tone')).toBe(false);
	});
});

describe('Chinese sentences', () => {
	it('line pinyin up with the word-bank cards', () => {
		const item = {
			...course.units[1].items[0],
			id: 'zh.s.t1',
			type: 'sentence' as const,
			text: '她是我女儿。',
			roman: "Tā shì wǒ nǚ'ér.",
			tokens: ['她', '是', '我', '女儿']
		};
		expect([...cardRoman(item)]).toEqual([
			['她', 'Tā'],
			['是', 'shì'],
			['我', 'wǒ'],
			['女儿', "nǚ'ér"]
		]);
	});
});

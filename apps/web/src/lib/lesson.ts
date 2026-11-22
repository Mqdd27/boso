// Lesson generator: a pure function of (unit, earlier units, item stats, lesson number, seed).
import { gloss, type GlossLang, type Item, type Unit } from './types.js';

export type Kind = 'meaning' | 'word' | 'listen';
export type Exercise =
	| { kind: 'intro'; item: Item }
	| { kind: Kind; item: Item; options: Item[] }
	| { kind: 'match'; items: Item[]; right: Item[] };

export type ItemStat = {
	id: string;
	seen: number;
	correct: number;
	wrong: number;
	lastSeen: string;
};

export type LessonInput = {
	unit: Unit;
	earlier: Unit[];
	stats: Record<string, ItemStat | undefined>;
	lesson: 1 | 2;
	seed: number;
	lang: GlossLang;
	canListen: boolean;
};

export const LESSON_SIZE = 11; // graded exercises per lesson (intro cards come on top)
export const MATCH_PAIRS = 5;

/** mulberry32: small, fast, good enough for shuffling. */
export function rng(seed: number): () => number {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

export function shuffle<T>(list: readonly T[], rand: () => number): T[] {
	const out = [...list];
	for (let i = out.length - 1; i > 0; i--) {
		const j = Math.floor(rand() * (i + 1));
		[out[i], out[j]] = [out[j], out[i]];
	}
	return out;
}

/**
 * Up to 3 wrong options from the unit and earlier units. None shares the answer's text or its gloss
 * in `lang` (누나 and 언니 can both be "kakak perempuan"), and no two options look the same.
 */
export function distractors(answer: Item, pool: Item[], lang: GlossLang, rand: () => number) {
	const texts = new Set([answer.text]);
	const glosses = new Set([gloss(answer, lang)]);
	const out: Item[] = [];
	for (const item of shuffle(pool, rand)) {
		if (out.length === 3) break;
		if (texts.has(item.text) || glosses.has(gloss(item, lang))) continue;
		texts.add(item.text);
		glosses.add(gloss(item, lang));
		out.push(item);
	}
	return out;
}

function choice(kind: Kind, item: Item, pool: Item[], lang: GlossLang, rand: () => number) {
	return { kind, item, options: shuffle([item, ...distractors(item, pool, lang, rand)], rand) };
}

function match(items: Item[], lang: GlossLang, rand: () => number): Exercise | null {
	// Pairs must be unambiguous: one gloss per item.
	const seen = new Set<string>();
	const picked = shuffle(items, rand)
		.filter((i) => !seen.has(gloss(i, lang)) && seen.add(gloss(i, lang)))
		.slice(0, MATCH_PAIRS);
	if (picked.length < 3) return null;
	return { kind: 'match', items: picked, right: shuffle(picked, rand) };
}

export function generateLesson(input: LessonInput): Exercise[] {
	const { unit, earlier, stats, lesson, lang, canListen } = input;
	const rand = rng(input.seed);
	const pool = [...unit.items, ...earlier.flatMap((u) => u.items)];
	const kinds: Kind[] = canListen ? ['meaning', 'word', 'listen'] : ['meaning', 'word'];
	const out: Exercise[] = [];
	const introduced = new Set<string>();
	let graded = 0;
	const add = (kind: Kind, item: Item) => {
		if (!stats[item.id]?.seen && !introduced.has(item.id)) {
			out.push({ kind: 'intro', item });
			introduced.add(item.id);
		}
		out.push(choice(kind, item, pool, lang, rand));
		graded++;
	};

	if (lesson === 1) {
		// Every new word: intro card, then recognise it. Then pairs, then fill up with mixed practice.
		unit.items.forEach((item, n) => add(n % 2 ? 'word' : 'meaning', item));
		const pairs = match(unit.items, lang, rand);
		if (pairs) {
			out.push(pairs);
			graded++;
		}
		for (const item of shuffle(unit.items, rand)) {
			if (graded >= LESSON_SIZE) break;
			add(kinds[graded % kinds.length], item);
		}
	} else {
		// Weak words first (more wrong than right), each word at least once, pairs in the middle.
		const weakness = (i: Item) => (stats[i.id]?.wrong ?? 0) - (stats[i.id]?.correct ?? 0);
		const order = shuffle(unit.items, rand).sort((a, b) => weakness(b) - weakness(a));
		const weak = order.filter((i) => weakness(i) > 0);
		const queue = [...order, ...weak, ...shuffle(unit.items, rand)];
		const pairsAt = Math.floor(LESSON_SIZE / 2);
		for (const item of queue) {
			if (graded >= LESSON_SIZE) break;
			if (graded === pairsAt) {
				const pairs = match(unit.items, lang, rand);
				if (pairs) {
					out.push(pairs);
					graded++;
				}
			}
			add(kinds[graded % kinds.length], item);
		}
	}
	return out;
}

/** After a wrong answer: the same exercise comes back at the end of the lesson. */
export function requeue(queue: Exercise[], index: number): Exercise[] {
	return [...queue, queue[index]];
}

export const LESSON_XP = 10;
export const PERFECT_BONUS = 5;
export const lessonXp = (mistakes: number) => LESSON_XP + (mistakes === 0 ? PERFECT_BONUS : 0);

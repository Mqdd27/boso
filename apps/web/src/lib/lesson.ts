// Lesson generator: a pure function of (unit, earlier units, item stats, lesson number, seed).
// Vocab units ask for meanings (glosses); script units (Hangul) ask for sounds (romanization).
import { decompose, FINALS, INITIALS, similar, VOWELS } from './hangul.js';
import { gloss, type GlossLang, type Item, type Unit } from './types.js';

export type Kind = 'meaning' | 'word' | 'listen';
export type Tiles = { initial: string[]; vowel: string[]; final: string[] }; // final: [] = none
export type Exercise =
	| { kind: 'intro'; item: Item }
	| { kind: Kind; item: Item; options: Item[] }
	| { kind: 'match'; items: Item[]; right: Item[] }
	| { kind: 'build'; item: Item; listen: boolean; tiles: Tiles };

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

export const isScript = (unit: Unit) => unit.kind === 'script';

/** Units open in order within their section (Hangul, vocab); the sections don't lock each other. */
export const section = (units: Unit[], script: boolean) =>
	units.filter((u) => isScript(u) === script);

/** What an item is matched against: its sound in script units, its meaning elsewhere. */
export const label = (item: Item, lang: GlossLang, script: boolean) =>
	script ? item.roman : gloss(item, lang);

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
 * Up to 3 wrong options from the pool. None shares the answer's text or its `key` (the gloss in the
 * shown language: 누나 and 언니 can both be "kakak perempuan"; the sound in script units: ㅑ and 야
 * are both "ya"), and no two options look the same. Look-alikes come first (ㅓ/ㅗ, ㄱ/ㅋ/ㄲ).
 */
export function distractors(
	answer: Item,
	pool: Item[],
	key: (item: Item) => string,
	rand: () => number
) {
	const texts = new Set([answer.text]);
	const keys = new Set([key(answer)]);
	const alike = pool.filter((i) => similar(i.text, answer.text));
	const rest = pool.filter((i) => !similar(i.text, answer.text));
	const out: Item[] = [];
	for (const item of [...shuffle(alike, rand), ...shuffle(rest, rand)]) {
		if (out.length === 3) break;
		if (texts.has(item.text) || keys.has(key(item))) continue;
		texts.add(item.text);
		keys.add(key(item));
		out.push(item);
	}
	return out;
}

function match(items: Item[], key: (item: Item) => string, rand: () => number): Exercise | null {
	// Pairs must be unambiguous: one key per item.
	const seen = new Set<string>();
	const picked = shuffle(items, rand)
		.filter((i) => !seen.has(key(i)) && seen.add(key(i)))
		.slice(0, MATCH_PAIRS);
	if (picked.length < 3) return null;
	return { kind: 'match', items: picked, right: shuffle(picked, rand) };
}

/** Script units: a vowel is asked among vowels, a consonant among consonants, a block among blocks. */
function shape(text: string) {
	if (decompose(text)) return 'block';
	if (VOWELS.includes(text)) return 'vowel';
	return INITIALS.includes(text) ? 'consonant' : 'other';
}

/** The answer's letter plus up to 3 others from `known` (look-alikes first), for one slot. */
function tiles(answer: string, known: Set<string>, rand: () => number): string[] {
	const others = [...known].filter((l) => l !== answer);
	const alike = shuffle(
		others.filter((l) => similar(l, answer)),
		rand
	);
	const rest = shuffle(
		others.filter((l) => !similar(l, answer)),
		rand
	);
	return shuffle([answer, ...[...alike, ...rest].slice(0, 3)], rand);
}

/** Build a syllable block from tiles. The tiles are letters the learner has already met. */
function build(item: Item, pool: Item[], listen: boolean, rand: () => number): Exercise {
	const parts = decompose(item.text)!;
	const known = { initial: new Set<string>(), vowel: new Set<string>(), final: new Set<string>() };
	for (const { text } of pool) {
		const p = decompose(text);
		if (p) {
			known.initial.add(p.initial);
			known.vowel.add(p.vowel);
			if (p.final) known.final.add(p.final);
		} else if (VOWELS.includes(text)) known.vowel.add(text);
		else if (INITIALS.includes(text)) known.initial.add(text);
	}
	for (const c of known.initial) if (FINALS.includes(c)) known.final.add(c);
	return {
		kind: 'build',
		item,
		listen,
		tiles: {
			initial: tiles(parts.initial, known.initial, rand),
			vowel: tiles(parts.vowel, known.vowel, rand),
			final: parts.final ? tiles(parts.final, known.final, rand) : []
		}
	};
}

type Mode = Kind | 'build';

export function generateLesson(input: LessonInput): Exercise[] {
	const { unit, earlier, stats, lesson, lang, canListen } = input;
	const rand = rng(input.seed);
	const script = isScript(unit);
	const key = (item: Item) => label(item, lang, script);
	// Options come from units of the same kind only: no Hangul letters among vocab answers.
	const pool = [unit, ...earlier.filter((u) => isScript(u) === script)].flatMap((u) => u.items);
	const block = (item: Item) => script && decompose(item.text) !== null;
	const kindsOf = (item: Item): Mode[] => {
		const base: Mode[] = block(item) ? ['build', 'meaning', 'word'] : ['meaning', 'word'];
		return canListen ? [...base, 'listen'] : base;
	};
	const out: Exercise[] = [];
	const introduced = new Set<string>();
	let graded = 0;
	const add = (mode: Mode, item: Item) => {
		if (!stats[item.id]?.seen && !introduced.has(item.id)) {
			out.push({ kind: 'intro', item });
			introduced.add(item.id);
		}
		if (mode === 'build') out.push(build(item, pool, canListen && rand() < 0.5, rand));
		else {
			const from = script ? pool.filter((i) => shape(i.text) === shape(item.text)) : pool;
			const options = shuffle([item, ...distractors(item, from, key, rand)], rand);
			out.push({ kind: mode, item, options });
		}
		graded++;
	};
	const next = (item: Item) => {
		const kinds = kindsOf(item);
		return kinds[graded % kinds.length];
	};

	if (lesson === 1) {
		// Every new item: intro card, then recognise (or build) it. Then pairs, then mixed practice.
		unit.items.forEach((item, n) => add(block(item) ? 'build' : n % 2 ? 'word' : 'meaning', item));
		const pairs = match(unit.items, key, rand);
		if (pairs) {
			out.push(pairs);
			graded++;
		}
		for (const item of shuffle(unit.items, rand)) {
			if (graded >= LESSON_SIZE) break;
			add(next(item), item);
		}
	} else {
		// Weak items first (more wrong than right), each item at least once, pairs in the middle.
		const weakness = (i: Item) => (stats[i.id]?.wrong ?? 0) - (stats[i.id]?.correct ?? 0);
		const order = shuffle(unit.items, rand).sort((a, b) => weakness(b) - weakness(a));
		const weak = order.filter((i) => weakness(i) > 0);
		const queue = [...order, ...weak, ...shuffle(unit.items, rand)];
		const pairsAt = Math.floor(LESSON_SIZE / 2);
		for (const item of queue) {
			if (graded >= LESSON_SIZE) break;
			if (graded === pairsAt) {
				const pairs = match(unit.items, key, rand);
				if (pairs) {
					out.push(pairs);
					graded++;
				}
			}
			add(next(item), item);
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

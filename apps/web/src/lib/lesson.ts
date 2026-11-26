// Lesson generator: a pure function of (unit, earlier units, item stats, lesson number, seed).
// Vocab units ask for meanings (glosses); Hangul units ask for sounds (romanization). Pinyin units
// show the sound itself, so they ask what it is (the gloss) and which tone it has.
import { decompose, FINALS, INITIALS, similar, VOWELS } from './hangul.js';
import { oneSyllable } from './pinyin.js';
import { gloss, type GlossLang, type Item, type Unit } from './types.js';

export type Kind = 'meaning' | 'word' | 'listen';
export const TONES = [1, 2, 3, 4, 5];
export type Tiles = { initial: string[]; vowel: string[]; final: string[] }; // final: [] = none
export type Exercise =
	| { kind: 'intro'; item: Item }
	| { kind: Kind; item: Item; options: Item[] }
	| { kind: 'match'; items: Item[]; right: Item[] }
	| { kind: 'build'; item: Item; listen: boolean; tiles: Tiles }
	| { kind: 'tone'; item: Item } // hear a syllable, pick its tone from TONES
	| { kind: 'arrange'; item: Item; listen: boolean; bank: string[]; roman: string[] }; // sentence from a word bank

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
export const SENTENCES_PER_LESSON = 3; // in lesson 2 and practice, when the unit has sentences
export const DECOYS = 2; // extra word-bank cards from other sentences

export const isSentence = (item: Item) => item.type === 'sentence';

/** Word-bank cards of a sentence (its eojeols without punctuation). */
export const cards = (item: Item) => item.tokens ?? [item.text];

const bare = (word: string) => word.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');

/** Romanization per card: `roman` has one word per eojeol, like `text`, so they line up. */
export function cardRoman(item: Item): Map<string, string> {
	const roman = item.roman.split(' ').map(bare);
	const words = item.text.split(' ');
	const tokens = cards(item);
	if (roman.length !== words.length || tokens.length !== words.length) return new Map();
	return new Map(tokens.map((t, n) => [t, roman[n]]));
}

/** A sentence's new (hinted) word as an intro-card item. */
function hintItem(item: Item, token: string, gloss: Item['gloss']): Item {
	const { source, license, author, review } = item;
	const roman = cardRoman(item).get(token) ?? '';
	const id = `${item.id.split('.')[0]}.hint.${token}`;
	return { id, type: 'word', text: token, roman, gloss, source, license, author, review };
}

/** A word-bank answer is right when it reads as the sentence: duplicate cards can go either way. */
export const arrangedRight = (picked: string[], item: Item) =>
	picked.join(' ') === cards(item).join(' ');

export const isScript = (unit: Unit) => unit.kind === 'script';

/** Units open in order within their section (Hangul, vocab); the sections don't lock each other. */
export const section = (units: Unit[], script: boolean) =>
	units.filter((u) => isScript(u) === script);

/** Hangul units ask for sounds; pinyin units are written as sounds already (text = roman). */
export const asksSound = (unit: Unit) =>
	isScript(unit) && unit.items.some((i) => i.text !== i.roman);

/** What an item is matched against: its sound in Hangul units, its meaning elsewhere. */
export const label = (item: Item, lang: GlossLang, sound: boolean) =>
	sound ? item.roman : gloss(item, lang);

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

/** The sentence's cards plus up to DECOYS cards from other sentences that it doesn't use. */
function bank(item: Item, sentences: Item[], rand: () => number): string[] {
	const own = cards(item);
	const others = [...new Set(sentences.filter((s) => s.id !== item.id).flatMap(cards))].sort();
	const decoys = shuffle(
		others.filter((t) => !own.includes(t)),
		rand
	).slice(0, DECOYS);
	return shuffle([...own, ...decoys], rand);
}

/** Romanization of each bank card, from whichever sentence it came from. */
function bankRoman(bank: string[], item: Item, sentences: Item[]): string[] {
	const known = new Map(sentences.flatMap((s) => [...cardRoman(s)]));
	for (const [t, r] of cardRoman(item)) known.set(t, r);
	return bank.map((t) => known.get(t) ?? '');
}

type Mode = Kind | 'build' | 'tone';

export function generateLesson(input: LessonInput): Exercise[] {
	const { unit, earlier, stats, lesson, lang, canListen } = input;
	const rand = rng(input.seed);
	const script = isScript(unit);
	const key = (item: Item) => label(item, lang, asksSound(unit));
	// Options come from units of the same kind only: no Hangul letters among vocab answers.
	const all = [unit, ...earlier.filter((u) => isScript(u) === script)].flatMap((u) => u.items);
	// Words and sentences are asked separately: a sentence is never an option for a word.
	const pool = all.filter((i) => !isSentence(i));
	const sentencePool = all.filter(isSentence);
	const words = unit.items.filter((i) => !isSentence(i));
	const sentences = lesson === 2 ? unit.items.filter(isSentence) : [];
	const size = LESSON_SIZE - Math.min(SENTENCES_PER_LESSON, sentences.length);
	const block = (item: Item) => script && decompose(item.text) !== null;
	// Tone pick needs the sound: single syllables only (a tone per item).
	const tonal = (item: Item) => canListen && oneSyllable(item.tones);
	const kindsOf = (item: Item): Mode[] => {
		const base: Mode[] = block(item) ? ['build', 'meaning', 'word'] : ['meaning', 'word'];
		if (!canListen) return base;
		return tonal(item) ? ['tone', ...base, 'listen'] : [...base, 'listen'];
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
		else if (mode === 'tone') out.push({ kind: 'tone', item });
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
		words.forEach((item, n) =>
			add(block(item) ? 'build' : script && tonal(item) ? 'tone' : n % 2 ? 'word' : 'meaning', item)
		);
		const pairs = match(words, key, rand);
		if (pairs) {
			out.push(pairs);
			graded++;
		}
		for (const item of shuffle(words, rand)) {
			if (graded >= size) break;
			add(next(item), item);
		}
	} else {
		// Weak items first (more wrong than right), each item at least once, pairs in the middle.
		const weakness = (i: Item) => (stats[i.id]?.wrong ?? 0) - (stats[i.id]?.correct ?? 0);
		const order = shuffle(words, rand).sort((a, b) => weakness(b) - weakness(a));
		const weak = order.filter((i) => weakness(i) > 0);
		const queue = [...order, ...weak, ...shuffle(words, rand)];
		const pairsAt = Math.floor(size / 2);
		for (const item of queue) {
			if (graded >= size) break;
			if (graded === pairsAt) {
				const pairs = match(words, key, rand);
				if (pairs) {
					out.push(pairs);
					graded++;
				}
			}
			add(next(item), item);
		}
		// Then sentences (weakest first): build it from the word bank, from its meaning or by ear,
		// or pick its meaning. No intro cards: every word in them is known, or has a hint.
		const picked = shuffle(sentences, rand)
			.sort((a, b) => weakness(b) - weakness(a))
			.slice(0, SENTENCES_PER_LESSON);
		const glossKey = (i: Item) => gloss(i, lang);
		picked.forEach((item, n) => {
			const others = distractors(item, sentencePool, glossKey, rand);
			const mode = n % 3 === 1 && others.length ? 'meaning' : 'arrange';
			if (mode === 'meaning') {
				out.push({ kind: 'meaning', item, options: shuffle([item, ...others], rand) });
			} else {
				// The English prompt doesn't show the new word, so introduce it first (once per sentence).
				if (!stats[item.id]?.seen)
					for (const h of item.hints ?? []) {
						const intro = hintItem(item, h.token, h.gloss);
						if (introduced.has(intro.id)) continue;
						introduced.add(intro.id);
						out.push({ kind: 'intro', item: intro });
					}
				const listen = canListen && n % 3 === 2;
				const cardsOf = bank(item, sentencePool, rand);
				const roman = bankRoman(cardsOf, item, sentencePool);
				out.push({ kind: 'arrange', item, listen, bank: cardsOf, roman });
			}
			graded++;
		});
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

// Spaced repetition (FSRS via ts-fsrs). Every graded item of a lesson or review session becomes a
// card; one answer per item per session: any mistake → Again, otherwise Good.
// Day-level scheduling (no minute learning steps): a review session is a daily thing.
import { DefaultScheduler, Rating } from 'ts-fsrs';
import { isScript } from './lesson.js';
import type { Item, Unit } from './types.js';

const scheduler = DefaultScheduler({ enableShortTerm: false, enableFuzz: false });
type FsrsCard = ReturnType<Awaited<typeof scheduler>['newCard']>;

export type SrsCard = { id: string; course: string; due: number; card: FsrsCard };
/** Append-only review log (one row per item per session): what M5 sync sends to the server. */
export type ReviewEvent = { id: string; ts: string; course: string; item: string; again: boolean };

/** Again for an item answered wrong at least once in the session, Good otherwise. */
export function grades(results: { id: string; correct: boolean }[]): Map<string, boolean> {
	const again = new Map<string, boolean>();
	for (const { id, correct } of results) again.set(id, (again.get(id) ?? false) || !correct);
	return again;
}

/** The next state of an item's card (a new card the first time). */
export async function schedule(
	previous: SrsCard | undefined,
	id: string,
	course: string,
	again: boolean,
	now: Date
): Promise<SrsCard> {
	const s = await scheduler;
	const card = previous?.card ?? s.newCard({ now });
	const next = s.review({ card, grade: again ? Rating.Again : Rating.Good, now }).card;
	return { id, course, due: next.dueAt.getTime(), card: next };
}

export const REVIEW_WORDS = 8;
export const REVIEW_SENTENCES = 3;

/** A review session as a unit of due items, so the lesson player can play it. Vocabulary first;
 *  script items (letters, pinyin) get their own session once no vocabulary is due, since the two
 *  kinds are asked differently. Most overdue first. */
export function reviewUnit(units: Unit[], due: SrsCard[]): Unit | null {
	const byId = new Map<string, [Unit, Item]>(
		units.flatMap((u) => u.items.map((i): [string, [Unit, Item]] => [i.id, [u, i]]))
	);
	const ordered = [...due]
		.sort((a, b) => a.due - b.due)
		.flatMap((c) => (byId.has(c.id) ? [byId.get(c.id)!] : []));
	for (const script of [false, true]) {
		const mine = ordered.filter(([u]) => isScript(u) === script).map(([, i]) => i);
		const words = mine.filter((i) => i.type !== 'sentence').slice(0, REVIEW_WORDS);
		const sentences = mine.filter((i) => i.type === 'sentence').slice(0, REVIEW_SENTENCES);
		if (!words.length && !sentences.length) continue;
		const first = ordered.find(([u]) => isScript(u) === script)![0];
		return { ...first, id: 'review', items: [...words, ...sentences] };
	}
	return null;
}

/** The units a review session asks options from, without the reviewed items (no duplicates). */
export function reviewPool(units: Unit[], review: Unit): Unit[] {
	const ids = new Set(review.items.map((i: Item) => i.id));
	return units.map((u) => ({ ...u, items: u.items.filter((i) => !ids.has(i.id)) }));
}

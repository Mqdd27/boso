import { describe, expect, it } from 'vitest';
import { grades, reviewPool, reviewUnit, schedule, type SrsCard } from './srs.js';
import type { Item, Unit } from './types.js';

const item = (id: string, type: Item['type'] = 'word'): Item => ({
	id,
	type,
	text: id,
	roman: id,
	gloss: { en: id },
	source: 'boso',
	license: 'CC BY-SA 4.0',
	review: 'needs_review'
});
const unit = (id: string, items: Item[], kind?: Unit['kind']): Unit => ({
	id,
	title: { en: id },
	level: 'x',
	kind,
	items
});
const DAY = 86_400_000;

describe('srs', () => {
	it('grades an item Again when any answer was wrong', () => {
		const g = grades([
			{ id: 'a', correct: true },
			{ id: 'b', correct: false },
			{ id: 'b', correct: true },
			{ id: 'a', correct: true }
		]);
		expect([...g]).toEqual([
			['a', false],
			['b', true]
		]);
	});

	it('schedules in days, longer after each right answer, back to soon after a miss', async () => {
		const now = new Date('2026-01-01T00:00:00Z');
		const first = await schedule(undefined, 'a', 'ko-en', false, now);
		expect(first.due - now.getTime()).toBeGreaterThanOrEqual(DAY);
		const later = new Date(first.due);
		const second = await schedule(first, 'a', 'ko-en', false, later);
		expect(second.due - later.getTime()).toBeGreaterThan(first.due - now.getTime());
		const missed = await schedule(second, 'a', 'ko-en', true, new Date(second.due));
		expect(missed.due - second.due).toBeLessThan(second.due - later.getTime());
		expect(missed.card.lapses).toBe(1);
	});

	it('builds a review unit: vocabulary first, most overdue first, capped', () => {
		const words = Array.from({ length: 10 }, (_, n) => item(`w${n}`));
		const units = [
			unit('script', [item('ㄱ')], 'script'),
			unit('v1', [...words, item('s1', 'sentence')])
		];
		const card = (id: string, due: number): SrsCard => ({
			id,
			course: 'ko-en',
			due,
			card: {} as never
		});
		const due = [
			card('ㄱ', 0),
			...words.map((w, n) => card(w.id, 100 - n)),
			card('s1', 5),
			card('gone', 1)
		];
		const r = reviewUnit(units, due)!;
		expect(r.id).toBe('review');
		expect(r.kind).toBeUndefined();
		expect(r.items.map((i) => i.id)).toEqual([
			'w9',
			'w8',
			'w7',
			'w6',
			'w5',
			'w4',
			'w3',
			'w2',
			's1'
		]);
		expect(reviewPool(units, r)[1].items.map((i) => i.id)).toEqual(['w0', 'w1']);
		// Only script items due: a script session.
		expect(reviewUnit(units, [card('ㄱ', 0)])!.kind).toBe('script');
		expect(reviewUnit(units, [card('gone', 0)])).toBeNull();
	});
});

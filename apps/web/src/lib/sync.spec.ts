import { describe, expect, it } from 'vitest';
import { key, mergeProgress } from './sync.js';

describe('sync', () => {
	it('merges unit progress from two devices', () => {
		const phone = { course: 'ko-en', unit: 'u1', lessons: [1], updatedAt: '2026-11-02' };
		const laptop = {
			course: 'ko-en',
			unit: 'u1',
			lessons: [1, 2],
			completedAt: '2026-11-01',
			updatedAt: '2026-11-01'
		};
		expect(mergeProgress(phone, laptop)).toEqual({
			course: 'ko-en',
			unit: 'u1',
			lessons: [1, 2],
			completedAt: '2026-11-01',
			updatedAt: '2026-11-02'
		});
	});

	it('versions rows by their newest timestamp, old rows still get sent', () => {
		expect(key.unitProgress({ course: 'ko-en', unit: 'u1', lessons: [1] })).toEqual({
			id: 'ko-en/u1',
			v: '0'
		});
		const card = { lastReviewAt: new Date('2026-11-02T00:00:00Z') } as never;
		expect(key.cards({ id: 'ko.w.ne', course: 'ko-en', due: 0, card }).v).toBe(
			'2026-11-02T00:00:00.000Z'
		);
	});
});

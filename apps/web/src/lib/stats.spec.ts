import { describe, expect, it } from 'vitest';
import {
	addDays,
	dailyTotals,
	level,
	localDate,
	range,
	streak,
	sumXp,
	weeks,
	type Activity
} from './stats.js';

const act = (localDate: string, xp: number, course = 'ko-en'): Activity => ({
	id: `${localDate}-${xp}-${course}`,
	ts: `${localDate}T10:00:00Z`,
	localDate,
	course,
	unit: 'ko-010-test',
	xp,
	lessons: 1,
	reviews: 0
});

describe('streak', () => {
	const goal = 20;

	it('counts consecutive days with the goal met, and the longest run', () => {
		const totals = dailyTotals([
			act('2026-11-01', 20),
			act('2026-11-02', 30),
			act('2026-11-03', 25), // run of 3
			act('2026-11-05', 15), // goal not met: gap
			act('2026-11-20', 20),
			act('2026-11-21', 10),
			act('2026-11-21', 10) // two lessons add up to the goal
		]);
		expect(streak(totals, goal, '2026-11-21')).toEqual({ current: 2, longest: 3 });
	});

	it("isn't broken while today's goal is still open", () => {
		const totals = dailyTotals([
			act('2026-11-20', 20),
			act('2026-11-21', 20),
			act('2026-11-22', 5)
		]);
		expect(streak(totals, goal, '2026-11-22').current).toBe(2);
		expect(streak(totals, goal, '2026-11-23').current).toBe(0); // yesterday missed: broken
	});

	it('is zero with no activity', () => {
		expect(streak(new Map(), goal, '2026-11-22')).toEqual({ current: 0, longest: 0 });
	});
});

describe('local dates', () => {
	it('uses the learner time zone, not UTC (Asia/Jakarta is UTC+7)', () => {
		const lateUtc = new Date('2026-11-21T18:30:00Z'); // 01:30 on the 22nd in Jakarta
		expect(localDate(lateUtc, 'Asia/Jakarta')).toBe('2026-11-22');
		expect(localDate(lateUtc, 'UTC')).toBe('2026-11-21');
		expect(localDate(new Date('2026-11-21T16:59:00Z'), 'Asia/Jakarta')).toBe('2026-11-21');
	});

	it('adds days across months and years', () => {
		expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
		expect(addDays('2026-03-01', -1)).toBe('2026-02-28');
	});
});

describe('heatmap', () => {
	it('maps XP to 5 levels', () => {
		expect([0, 1, 9, 10, 29, 30, 59, 60, 200].map(level)).toEqual([0, 1, 1, 2, 2, 3, 3, 4, 4]);
	});

	it('aggregates per day and filters per course', () => {
		const a = [act('2026-11-22', 15), act('2026-11-22', 10), act('2026-11-22', 5, 'zh-en')];
		expect(dailyTotals(a).get('2026-11-22')).toEqual({ xp: 30, lessons: 3, reviews: 0 });
		expect(dailyTotals(a, 'ko-en').get('2026-11-22')?.xp).toBe(25);
	});

	it('builds Monday- or Sunday-first week columns over the last year', () => {
		const [from, to] = range('last', '2026-11-22'); // a Sunday
		expect(from).toBe('2025-11-23');
		const monday = weeks(from, to, 1);
		expect(monday.length).toBe(53);
		expect(monday.every((w) => w.length === 7)).toBe(true);
		expect(monday.at(-1)!.at(-1)).toBe('2026-11-22'); // Sunday ends a Monday-first week
		expect(monday.flat().filter(Boolean).length).toBe(365);
		const sunday = weeks(from, to, 0);
		expect(sunday.at(-1)![0]).toBe('2026-11-22');
		expect(
			sunday
				.at(-1)!
				.slice(1)
				.every((d) => d === null)
		).toBe(true);
	});

	it('sums XP in a range', () => {
		const totals = dailyTotals([act('2025-12-31', 50), act('2026-01-01', 20)]);
		expect(sumXp(totals, ...range(2026, '2026-11-22'))).toBe(20);
	});
});

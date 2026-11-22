import { Dexie, type Table } from 'dexie';
import type { ItemStat } from './lesson.js';
import { localDate, type Activity } from './stats.js';

export type UnitProgress = {
	course: string;
	unit: string;
	lessons: number[];
	completedAt?: string;
};
export type Setting = { key: string; value: unknown };

class BosoDB extends Dexie {
	activity!: Table<Activity, string>;
	unitProgress!: Table<UnitProgress, [string, string]>;
	itemStats!: Table<ItemStat, string>;
	settings!: Table<Setting, string>;

	constructor() {
		super('boso');
		this.version(1).stores({
			activity: 'id, localDate, course', // append-only: the sync format for M5
			unitProgress: '[course+unit]',
			itemStats: 'id',
			settings: 'key'
		});
	}
}

export const db = new BosoDB();

export const LESSONS_PER_UNIT = 2;

/** Record a finished lesson: one activity event, unit progress, per-item stats. */
export async function recordLesson(r: {
	course: string;
	unit: string;
	lesson: number;
	xp: number;
	results: { id: string; correct: boolean }[];
	now?: Date;
}) {
	const now = r.now ?? new Date();
	const ts = now.toISOString();
	await db.transaction('rw', db.activity, db.unitProgress, db.itemStats, async () => {
		await db.activity.add({
			id: crypto.randomUUID(),
			ts,
			localDate: localDate(now),
			course: r.course,
			unit: r.unit,
			xp: r.xp,
			lessons: 1,
			reviews: 0
		});
		const p = (await db.unitProgress.get([r.course, r.unit])) ?? {
			course: r.course,
			unit: r.unit,
			lessons: []
		};
		if (!p.lessons.includes(r.lesson)) p.lessons = [...p.lessons, r.lesson].sort();
		if (!p.completedAt && p.lessons.length >= LESSONS_PER_UNIT) p.completedAt = ts;
		await db.unitProgress.put(p);
		for (const { id, correct } of r.results) {
			const s = (await db.itemStats.get(id)) ?? { id, seen: 0, correct: 0, wrong: 0, lastSeen: ts };
			s.seen++;
			s[correct ? 'correct' : 'wrong']++;
			s.lastSeen = ts;
			await db.itemStats.put(s);
		}
	});
}

export async function resetProgress() {
	await db.transaction('rw', db.activity, db.unitProgress, db.itemStats, async () => {
		await Promise.all([db.activity.clear(), db.unitProgress.clear(), db.itemStats.clear()]);
	});
}

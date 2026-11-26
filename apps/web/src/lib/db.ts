import { Dexie, type Table } from 'dexie';
import type { ItemStat } from './lesson.js';
import { grades, schedule, type ReviewEvent, type SrsCard } from './srs.js';
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
	cards!: Table<SrsCard, string>;
	reviews!: Table<ReviewEvent, string>;

	constructor() {
		super('boso');
		this.version(1).stores({
			activity: 'id, localDate, course', // append-only: the sync format for M5
			unitProgress: '[course+unit]',
			itemStats: 'id',
			settings: 'key'
		});
		this.version(2).stores({
			cards: 'id, due, [course+due]',
			reviews: 'id, ts, course' // append-only, like activity
		});
	}
}

export const db = new BosoDB();

export const LESSONS_PER_UNIT = 2;

/** Record a finished lesson or review session: one activity event, unit progress (lessons only),
 *  per-item stats, and the items' next review dates. */
export async function recordLesson(r: {
	course: string;
	unit: string;
	lesson: number;
	xp: number;
	results: { id: string; correct: boolean }[];
	review?: boolean;
	now?: Date;
}) {
	const now = r.now ?? new Date();
	const ts = now.toISOString();
	// Scheduling is async (ts-fsrs), so it happens before the transaction.
	const again = grades(r.results);
	const previous = await db.cards.bulkGet([...again.keys()]);
	const cards = await Promise.all(
		[...again].map(([id, a], n) => schedule(previous[n], id, r.course, a, now))
	);
	const tables = [db.activity, db.unitProgress, db.itemStats, db.cards, db.reviews];
	await db.transaction('rw', tables, async () => {
		await db.activity.add({
			id: crypto.randomUUID(),
			ts,
			localDate: localDate(now),
			course: r.course,
			unit: r.unit,
			xp: r.xp,
			lessons: r.review ? 0 : 1,
			reviews: r.review ? again.size : 0
		});
		await db.cards.bulkPut(cards);
		await db.reviews.bulkAdd(
			[...again].map(([item, a]) => ({
				id: crypto.randomUUID(),
				ts,
				course: r.course,
				item,
				again: a
			}))
		);
		if (r.review) return itemStats(r.results, ts);
		const p = (await db.unitProgress.get([r.course, r.unit])) ?? {
			course: r.course,
			unit: r.unit,
			lessons: []
		};
		if (!p.lessons.includes(r.lesson)) p.lessons = [...p.lessons, r.lesson].sort();
		if (!p.completedAt && p.lessons.length >= LESSONS_PER_UNIT) p.completedAt = ts;
		await db.unitProgress.put(p);
		await itemStats(r.results, ts);
	});
}

async function itemStats(results: { id: string; correct: boolean }[], ts: string) {
	for (const { id, correct } of results) {
		const s = (await db.itemStats.get(id)) ?? { id, seen: 0, correct: 0, wrong: 0, lastSeen: ts };
		s.seen++;
		s[correct ? 'correct' : 'wrong']++;
		s.lastSeen = ts;
		await db.itemStats.put(s);
	}
}

export async function resetProgress() {
	const tables = [db.activity, db.unitProgress, db.itemStats, db.cards, db.reviews];
	await db.transaction('rw', tables, async () => {
		await Promise.all(tables.map((t) => t.clear()));
	});
}

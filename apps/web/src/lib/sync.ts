// Sync with the server (M5c). Every synced row is a document {kind, id, v, data}: the server keeps
// the one with the largest v (an ISO timestamp) and hands out changes in order, the client merges.
// Append-only events (activity, reviews) never conflict; cards and item stats keep the newest;
// unit progress is a union of the lessons done on every device.
import { me } from './account.js';
import { db, type UnitProgress } from './db.js';
import type { ItemStat } from './lesson.js';
import type { ReviewEvent, SrsCard } from './srs.js';
import type { Activity } from './stats.js';

type Rows = {
	activity: Activity;
	reviews: ReviewEvent;
	cards: SrsCard;
	unitProgress: UnitProgress;
	itemStats: ItemStat;
};
export type Kind = keyof Rows;
export type Doc = { kind: Kind; id: string; v: string; data: unknown };
type State = { email: string; cursor: number; pushed: Partial<Record<Kind, string>> };

const BATCH = 500; // the server's limit per request

const iso = (d: Date | string | null | undefined) => (d ? new Date(d).toISOString() : '');

/** A row's id and version. Rows from before sync have no version field: '0' still sends them. */
export const key: { [K in Kind]: (r: Rows[K]) => { id: string; v: string } } = {
	activity: (r) => ({ id: r.id, v: r.ts }),
	reviews: (r) => ({ id: r.id, v: r.ts }),
	cards: (r) => ({ id: r.id, v: iso(r.card.lastReviewAt) || '0' }),
	unitProgress: (r) => ({
		id: `${r.course}/${r.unit}`,
		v: r.updatedAt ?? r.completedAt ?? '0'
	}),
	itemStats: (r) => ({ id: r.id, v: r.lastSeen })
};

/** Local rows changed since the last push (larger v than the largest one pushed). */
async function changed(pushed: State['pushed']): Promise<Doc[]> {
	const docs: Doc[] = [];
	for (const kind of Object.keys(key) as Kind[]) {
		const rows = (await db.table(kind).toArray()) as Rows[Kind][];
		for (const r of rows) {
			const { id, v } = (key[kind] as (r: Rows[Kind]) => { id: string; v: string })(r);
			if (v > (pushed[kind] ?? '')) docs.push({ kind, id, v, data: r });
		}
	}
	return docs;
}

/** Merge pulled docs into the local tables. Exported for tests. */
export async function apply(docs: Doc[]) {
	const tables = [db.activity, db.reviews, db.cards, db.unitProgress, db.itemStats];
	await db.transaction('rw', tables, async () => {
		for (const d of docs) {
			if (d.kind === 'activity') await db.activity.put(d.data as Activity);
			else if (d.kind === 'reviews') await db.reviews.put(d.data as ReviewEvent);
			else if (d.kind === 'cards') {
				const c = d.data as SrsCard;
				// JSON turned the card's dates into strings; ts-fsrs needs Dates.
				c.card = { ...c.card, dueAt: new Date(c.card.dueAt) };
				if (c.card.lastReviewAt) c.card.lastReviewAt = new Date(c.card.lastReviewAt);
				const mine = await db.cards.get(c.id);
				if (!mine || d.v > key.cards(mine).v) await db.cards.put(c);
			} else if (d.kind === 'itemStats') {
				const s = d.data as ItemStat;
				const mine = await db.itemStats.get(s.id);
				if (!mine || s.lastSeen > mine.lastSeen) await db.itemStats.put(s);
			} else if (d.kind === 'unitProgress') {
				const p = d.data as UnitProgress;
				const mine = await db.unitProgress.get([p.course, p.unit]);
				await db.unitProgress.put(mine ? mergeProgress(mine, p) : p);
			}
		}
	});
}

export function mergeProgress(a: UnitProgress, b: UnitProgress): UnitProgress {
	const done = [a.completedAt, b.completedAt].filter((t): t is string => !!t).sort();
	const updated = [a.updatedAt, b.updatedAt].filter((t): t is string => !!t).sort();
	return {
		course: a.course,
		unit: a.unit,
		lessons: [...new Set([...a.lessons, ...b.lessons])].sort(),
		...(done.length ? { completedAt: done[0] } : {}),
		...(updated.length ? { updatedAt: updated.at(-1) } : {})
	};
}

let running: Promise<'synced' | 'off' | 'failed'> | null = null;

/** Push local changes and pull the account's. 'off' = not logged in or no server. Never throws;
 *  the app works the same without it. */
export function sync(): Promise<'synced' | 'off' | 'failed'> {
	running ??= run().finally(() => (running = null));
	return running;
}

async function run(): Promise<'synced' | 'off' | 'failed'> {
	const account = await me();
	if (!account || account === 'unavailable') return 'off';
	try {
		const saved = (await db.settings.get('sync'))?.value as State | undefined;
		// Another account on this device: send everything, pull from the start.
		const state: State =
			saved?.email === account.email ? saved : { email: account.email, cursor: 0, pushed: {} };
		const todo = await changed(state.pushed);
		let more = true;
		while (more || todo.length) {
			const batch = todo.splice(0, BATCH);
			const res = await fetch('/api/sync', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'same-origin',
				body: JSON.stringify({ since: state.cursor, docs: batch })
			});
			if (!res.ok) return 'failed';
			const page = (await res.json()) as { docs: Doc[]; cursor: number; more: boolean };
			await apply(page.docs);
			for (const d of batch) if (d.v > (state.pushed[d.kind] ?? '')) state.pushed[d.kind] = d.v;
			state.cursor = page.cursor;
			more = page.more;
			await db.settings.put({ key: 'sync', value: state });
		}
		return 'synced';
	} catch {
		return 'failed';
	}
}

// Streak + heatmap, always derived from the append-only activity log (never stored as counters).

export type Activity = {
	id: string;
	ts: string;
	localDate: string; // YYYY-MM-DD in the learner's time zone
	course: string;
	unit: string;
	xp: number;
	lessons: number;
	reviews: number;
};

export type DayTotal = { xp: number; lessons: number; reviews: number };

/** YYYY-MM-DD of `date` in `timeZone` (default: the device's). */
export function localDate(date: Date, timeZone?: string): string {
	return new Intl.DateTimeFormat('en-CA', {
		timeZone,
		year: 'numeric',
		month: '2-digit',
		day: '2-digit'
	}).format(date);
}

export function addDays(day: string, n: number): string {
	const d = new Date(`${day}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() + n);
	return d.toISOString().slice(0, 10);
}

/** 0 = Sunday … 6 = Saturday. */
export const weekday = (day: string) => new Date(`${day}T00:00:00Z`).getUTCDay();

export function dailyTotals(activity: Activity[], course?: string): Map<string, DayTotal> {
	const out = new Map<string, DayTotal>();
	for (const a of activity) {
		if (course && a.course !== course) continue;
		const t = out.get(a.localDate) ?? { xp: 0, lessons: 0, reviews: 0 };
		t.xp += a.xp;
		t.lessons += a.lessons;
		t.reviews += a.reviews;
		out.set(a.localDate, t);
	}
	return out;
}

/**
 * Days in a row with the daily goal met. If today's goal isn't met yet the streak still counts up
 * to yesterday: it only breaks once the day is over.
 */
export function streak(totals: Map<string, DayTotal>, goal: number, today: string) {
	const met = (day: string) => (totals.get(day)?.xp ?? 0) >= goal;
	let current = 0;
	for (let day = met(today) ? today : addDays(today, -1); met(day); day = addDays(day, -1)) {
		current++;
	}
	let longest = 0;
	let run = 0;
	let prev = '';
	for (const day of [...totals.keys()].filter(met).sort()) {
		run = prev && addDays(prev, 1) === day ? run + 1 : 1;
		longest = Math.max(longest, run);
		prev = day;
	}
	return { current, longest };
}

/** Heatmap intensity: 0, 1–9, 10–29, 30–59, 60+ XP. */
export function level(xp: number): 0 | 1 | 2 | 3 | 4 {
	if (xp <= 0) return 0;
	if (xp < 10) return 1;
	if (xp < 30) return 2;
	if (xp < 60) return 3;
	return 4;
}

/**
 * Week columns (7 days each, starting on `weekStart`: 1 = Monday, 0 = Sunday) covering
 * `from`..`to`. Days outside the range are null.
 */
export function weeks(from: string, to: string, weekStart: 0 | 1): (string | null)[][] {
	let start = from;
	while (weekday(start) !== weekStart) start = addDays(start, -1);
	const out: (string | null)[][] = [];
	for (let day = start; day <= to;) {
		const week: (string | null)[] = [];
		for (let i = 0; i < 7; i++, day = addDays(day, 1)) {
			week.push(day >= from && day <= to ? day : null);
		}
		out.push(week);
	}
	return out;
}

/** The heatmap range: the last 365 days up to today, or one calendar year. */
export function range(year: number | 'last', today: string): [string, string] {
	return year === 'last' ? [addDays(today, -364), today] : [`${year}-01-01`, `${year}-12-31`];
}

export function sumXp(totals: Map<string, DayTotal>, from: string, to: string): number {
	let xp = 0;
	for (const [day, t] of totals) if (day >= from && day <= to) xp += t.xp;
	return xp;
}

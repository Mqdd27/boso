import { db } from './db.js';

export type Theme = 'system' | 'light' | 'dark';
export type Settings = {
	romanization: boolean;
	romanizationByCourse: Record<string, boolean>; // missing = follow the global setting
	dailyGoal: number;
	weekStart: 0 | 1;
	theme: Theme;
	contributor: boolean;
	autoplay: boolean;
	learnScript: boolean; // show the script path (Hangul) on the home screen
};

export const DAILY_GOALS = [10, 20, 30, 50];
const defaults: Settings = {
	romanization: true,
	romanizationByCourse: {},
	dailyGoal: 20,
	weekStart: 1,
	theme: 'system',
	contributor: false,
	autoplay: true,
	learnScript: true
};

export const settings: Settings = $state({ ...defaults });

export async function loadSettings() {
	const row = await db.settings.get('app');
	Object.assign(settings, defaults, (row?.value as Partial<Settings>) ?? {});
}

export function saveSettings() {
	return db.settings.put({ key: 'app', value: $state.snapshot(settings) });
}

export const showRoman = (course: string) =>
	settings.romanizationByCourse[course] ?? settings.romanization;

/** Contributor mode, or any dev build: show "unreviewed" badges (SPEC §4.1). */
export const showReview = () => settings.contributor || import.meta.env.DEV;

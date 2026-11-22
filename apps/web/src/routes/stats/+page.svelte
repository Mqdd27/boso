<script lang="ts">
	import Heatmap from '#lib/components/Heatmap.svelte';
	import { db } from '#lib/db.js';
	import { listCourses, loadPack } from '#lib/pack.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { settings } from '#lib/settings.svelte.js';
	import { dailyTotals, localDate, range, streak, sumXp, type Activity } from '#lib/stats.js';
	import { localized } from '#lib/types.js';

	const lang = getLocale();
	const today = localDate(new Date());
	let activity = $state<Activity[]>([]);
	let courses = $state<{ id: string; name: string }[]>([]);
	let year = $state<'last' | number>('last');
	let course = $state('');

	void db.activity.toArray().then((a) => (activity = a));
	void listCourses().then(async (ids) => {
		courses = await Promise.all(
			ids.map(async (id) => {
				const title = await loadPack(id).then(
					(p) => p.course.title,
					() => undefined
				);
				return { id, name: title ? localized(title, lang) : id };
			})
		);
	});

	const totals = $derived(dailyTotals(activity, course || undefined));
	const [from, to] = $derived(range(year, today));
	const years = $derived.by(() => {
		const first = Math.min(
			Number(today.slice(0, 4)),
			...activity.map((a) => +a.localDate.slice(0, 4))
		);
		const out = [];
		for (let y = Number(today.slice(0, 4)); y >= first; y--) out.push(y);
		return out;
	});
	const s = $derived(streak(totals, settings.dailyGoal, today));
	const lessons = $derived([...totals.values()].reduce((n, t) => n + t.lessons, 0));
	const total = $derived([...totals.values()].reduce((n, t) => n + t.xp, 0));
</script>

<h1 class="mb-4 text-2xl font-bold">{m.stats_title()}</h1>

<div class="mb-4 flex flex-wrap gap-3">
	<label class="flex flex-col text-sm">
		{m.stats_year()}
		<select class="min-h-11 rounded-lg border px-2 dark:bg-zinc-900" bind:value={year}>
			<option value="last">{m.stats_last_year()}</option>
			{#each years as y (y)}<option value={y}>{y}</option>{/each}
		</select>
	</label>
	<label class="flex flex-col text-sm">
		{m.stats_course()}
		<select class="min-h-11 rounded-lg border px-2 dark:bg-zinc-900" bind:value={course}>
			<option value="">{m.stats_all_courses()}</option>
			{#each courses as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
		</select>
	</label>
</div>

<p class="mb-2 font-semibold" data-testid="year-xp">
	{year === 'last'
		? m.stats_year_xp({ xp: sumXp(totals, from, to) })
		: m.stats_range_xp({ xp: sumXp(totals, from, to), year })}
</p>
<Heatmap {totals} {from} {to} weekStart={settings.weekStart} locale={lang} />

<section class="mt-6 grid gap-1">
	<p>🔥 {m.streak_current({ days: s.current })}</p>
	<p>{m.streak_longest({ days: s.longest })}</p>
	<p>{m.stats_total_xp({ xp: total })}</p>
	<p>{m.stats_total_lessons({ count: lessons })}</p>
</section>

<script lang="ts">
	import Heatmap from '#lib/components/Heatmap.svelte';
	import Icon from '#lib/components/Icon.svelte';
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

	let unitsDone = $state(0);
	void db.activity.toArray().then((a) => (activity = a));
	void db.unitProgress.toArray().then((p) => (unitsDone = p.filter((u) => u.completedAt).length));
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

<h1 class="pt-6 text-3xl font-black">{m.stats_title()}</h1>

<ul class="mt-5 grid grid-cols-2 gap-3" data-testid="stat-cards">
	{#each [{ value: s.current, label: m.stats_card_streak(), icon: 'flame', tone: 'text-orange-ink', title: m.streak_longest( { days: s.longest } ) }, { value: total, label: m.stats_card_xp(), icon: 'bolt', tone: 'text-gold-ink', title: m.stats_total_xp( { xp: total } ) }, { value: unitsDone, label: m.stats_card_units(), icon: 'star', tone: 'text-green-ink', title: m.stats_card_units() }, { value: lessons, label: m.stats_card_lessons(), icon: 'check', tone: 'text-blue-ink', title: m.stats_total_lessons( { count: lessons } ) }] as const as card (card.label)}
		<li
			class="flex items-center gap-3 rounded-card border-2 border-line px-3 py-3"
			title={card.title}
		>
			<Icon name={card.icon} size={30} filled={card.icon !== 'check'} class={card.tone} />
			<div>
				<p class="text-xl leading-tight font-black">{card.value}</p>
				<p class="text-sm font-bold text-muted">{card.label}</p>
			</div>
		</li>
	{/each}
</ul>
<p class="mt-2 px-1 text-sm text-muted">{m.streak_longest({ days: s.longest })}</p>

<h2 class="label mt-7 mb-2 px-1 text-muted">{m.heatmap_label()}</h2>
<section class="rounded-card border-2 border-line p-4">
	<div class="mb-4 flex flex-wrap gap-3">
		<label class="flex flex-col gap-1 text-sm font-bold text-muted">
			{m.stats_year()}
			<select
				class="min-h-11 rounded-chip border-2 border-line bg-bg px-2 font-bold text-ink"
				bind:value={year}
			>
				<option value="last">{m.stats_last_year()}</option>
				{#each years as y (y)}<option value={y}>{y}</option>{/each}
			</select>
		</label>
		<label class="flex flex-col gap-1 text-sm font-bold text-muted">
			{m.stats_course()}
			<select
				class="min-h-11 rounded-chip border-2 border-line bg-bg px-2 font-bold text-ink"
				bind:value={course}
			>
				<option value="">{m.stats_all_courses()}</option>
				{#each courses as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
			</select>
		</label>
	</div>

	<p class="mb-3 font-extrabold" data-testid="year-xp">
		{year === 'last'
			? m.stats_year_xp({ xp: sumXp(totals, from, to) })
			: m.stats_range_xp({ xp: sumXp(totals, from, to), year })}
	</p>
	<Heatmap {totals} {from} {to} weekStart={settings.weekStart} locale={lang} />
</section>

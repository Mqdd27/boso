<script lang="ts">
	import { resolve } from '$app/paths';
	import CourseGate from '#lib/components/CourseGate.svelte';
	import { db, LESSONS_PER_UNIT, type UnitProgress } from '#lib/db.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { settings } from '#lib/settings.svelte.js';
	import { dailyTotals, localDate, streak } from '#lib/stats.js';
	import { localized, type Pack } from '#lib/types.js';

	const lang = getLocale();
	const data = Promise.all([db.activity.toArray(), db.unitProgress.toArray()]).then(
		([activity, progress]) => {
			const totals = dailyTotals(activity);
			const today = localDate(new Date());
			return {
				today: totals.get(today)?.xp ?? 0,
				streak: streak(totals, settings.dailyGoal, today),
				progress: new Map(progress.map((p) => [`${p.course}/${p.unit}`, p]))
			};
		}
	);

	type Status = 'locked' | 'open' | 'done';
	function statuses(course: string, units: { id: string }[], progress: Map<string, UnitProgress>) {
		let prevDone = true;
		return units.map((u): Status => {
			const p = progress.get(`${course}/${u.id}`);
			const status = p?.completedAt ? 'done' : prevDone ? 'open' : 'locked';
			prevDone = !!p?.completedAt;
			return status;
		});
	}
</script>

<CourseGate>
	{#snippet children(packs: Pack[])}
		{#await data then d}
			<section
				class="mb-6 grid gap-2 rounded-2xl bg-zinc-100 p-4 dark:bg-zinc-900"
				data-testid="summary"
			>
				<p class="text-lg font-semibold">🔥 {m.streak_current({ days: d.streak.current })}</p>
				<p class="text-sm opacity-70">{m.streak_longest({ days: d.streak.longest })}</p>
				<p data-testid="xp-today">{m.xp_today({ xp: d.today })}</p>
				<div>
					<p class="text-sm">{m.daily_goal_progress({ xp: d.today, goal: settings.dailyGoal })}</p>
					<div class="mt-1 h-2 overflow-hidden rounded-full bg-zinc-300 dark:bg-zinc-700">
						<div
							class="h-full bg-amber-500"
							style:width="{Math.min(100, (100 * d.today) / settings.dailyGoal)}%"
						></div>
					</div>
				</div>
			</section>

			{#each packs as { course } (course.id)}
				{@const status = statuses(course.id, course.units, d.progress)}
				<h1 class="mb-3 text-2xl font-bold">
					{course.title ? localized(course.title, lang) : course.id}
				</h1>
				<ol class="flex flex-col gap-2" data-testid="units">
					{#each course.units as unit, n (unit.id)}
						{@const p = d.progress.get(`${course.id}/${unit.id}`)}
						<li data-unit={unit.id} data-status={status[n]}>
							{#if status[n] === 'locked'}
								<div
									class="flex min-h-16 items-center justify-between gap-3 rounded-2xl border p-4 opacity-50"
								>
									<span class="font-semibold">{localized(unit.title, lang)}</span>
									<span class="text-sm">🔒 {m.unit_locked()}</span>
								</div>
							{:else}
								<a
									href={resolve('/learn/[course]/[unit]', { course: course.id, unit: unit.id })}
									class="flex min-h-16 items-center justify-between gap-3 rounded-2xl border-2 p-4 {status[
										n
									] === 'done'
										? 'border-green-600'
										: 'border-sky-500'}"
								>
									<span>
										<span class="block font-semibold">{localized(unit.title, lang)}</span>
										<span class="text-sm opacity-70">
											{m.unit_words({ count: unit.items.length })} · {m.unit_lessons({
												done: p?.lessons.length ?? 0,
												total: LESSONS_PER_UNIT
											})}
										</span>
									</span>
									<span class="text-sm font-semibold">
										{status[n] === 'done'
											? `✓ ${m.unit_done()}`
											: p?.lessons.length
												? m.unit_continue()
												: m.unit_open()}
									</span>
								</a>
							{/if}
						</li>
					{/each}
				</ol>
			{/each}
		{/await}
	{/snippet}
</CourseGate>

<script lang="ts">
	import { tick } from 'svelte';
	import CourseGate from '#lib/components/CourseGate.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import LessonNode from '#lib/components/LessonNode.svelte';
	import { db, LESSONS_PER_UNIT, type UnitProgress } from '#lib/db.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { settings } from '#lib/settings.svelte.js';
	import { dailyTotals, localDate, streak } from '#lib/stats.js';
	import { isScript, section } from '#lib/lesson.js';
	import { localized, type NodeState, type Pack, type Unit } from '#lib/types.js';

	const lang = getLocale();
	const data = Promise.all([db.activity.toArray(), db.unitProgress.toArray()]).then(
		([activity, progress]) => {
			const totals = dailyTotals(activity);
			const today = localDate(new Date());
			return {
				today: totals.get(today)?.xp ?? 0,
				total: [...totals.values()].reduce((n, t) => n + t.xp, 0),
				streak: streak(totals, settings.dailyGoal, today),
				progress: new Map(progress.map((p) => [`${p.course}/${p.unit}`, p]))
			};
		}
	);

	type Status = 'locked' | 'open' | 'done';
	function statuses(course: string, units: Unit[], progress: Map<string, UnitProgress>) {
		let prevDone = true;
		return units.map((u): Status => {
			const p = progress.get(`${course}/${u.id}`);
			const status = p?.completedAt ? 'done' : prevDone ? 'open' : 'locked';
			prevDone = !!p?.completedAt;
			return status;
		});
	}

	/** Lesson n (1-based) of a unit: done, the next one to play, or not yet. */
	function nodeState(status: Status, p: UnitProgress | undefined, n: number): NodeState {
		if (status !== 'open') return status === 'done' ? 'done' : 'locked';
		if (p?.lessons.includes(n)) return 'done';
		const next = Array.from({ length: LESSONS_PER_UNIT }, (_, i) => i + 1).find(
			(l) => !p?.lessons.includes(l)
		);
		return n === next ? 'active' : 'locked';
	}

	// Zig-zag: a sine wave over the nodes of a section.
	const offset = (i: number) => Math.round(Math.sin((i * Math.PI) / 4) * 72);
	const BADGE: Record<string, string> = { ko: '한', zh: '中' };

	let openNode = $state<string | null>(null);

	function onclick(e: MouseEvent) {
		if (!(e.target as Element).closest('[data-node-wrap]')) openNode = null;
	}
	function onkeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') openNode = null;
	}

	// Bring the lesson to play next into view.
	void data.then(async () => {
		await tick();
		await tick();
		document.querySelector('[data-autoscroll]')?.scrollIntoView({ block: 'center' });
	});
</script>

<svelte:window {onclick} {onkeydown} />

<CourseGate>
	{#snippet children(packs: Pack[])}
		{#await data then d}
			{@const lead = packs[0].course}
			<header
				class="sticky top-0 z-10 -mx-4 flex h-14 items-center justify-between gap-3 border-b-2 border-line bg-bg px-4"
				data-testid="topbar"
			>
				<span class="flex items-center gap-2 font-extrabold">
					<span
						class="flex size-9 items-center justify-center rounded-lg border-b-4 border-purple-shade bg-purple-fill text-lg text-white"
						lang={lead.id.slice(0, 2)}
						aria-hidden="true"
					>
						{BADGE[lead.id.slice(0, 2)] ?? lead.id.slice(0, 2)}
					</span>
					<span class="label text-muted">{lead.id}</span>
				</span>
				<span class="flex items-center gap-4 text-lg font-extrabold">
					<span
						class="flex items-center gap-1 {d.streak.current ? 'text-orange-ink' : 'text-muted'}"
						aria-label={m.streak_current({ days: d.streak.current })}
						data-testid="streak"
					>
						<Icon name="flame" filled />{d.streak.current}
					</span>
					<span
						class="flex items-center gap-1 text-gold-ink"
						aria-label={m.stats_total_xp({ xp: d.total })}
					>
						<Icon name="bolt" filled />{d.total}
					</span>
				</span>
			</header>

			<section
				class="mt-4 flex items-center gap-4 rounded-card border-2 border-line p-4"
				data-testid="summary"
			>
				<Icon name="target" size={36} class="text-gold-ink" />
				<div class="flex-1">
					<p class="font-extrabold" data-testid="xp-today">{m.xp_today({ xp: d.today })}</p>
					<div
						class="mt-1.5 h-4 overflow-hidden rounded-full bg-locked-fill"
						role="progressbar"
						aria-label={m.daily_goal_progress({ xp: d.today, goal: settings.dailyGoal })}
						aria-valuemin={0}
						aria-valuemax={settings.dailyGoal}
						aria-valuenow={Math.min(d.today, settings.dailyGoal)}
					>
						<div
							class="h-full rounded-full bg-gold-fill"
							style:width="{Math.min(100, (100 * d.today) / settings.dailyGoal)}%"
						></div>
					</div>
					<p class="mt-1 text-sm text-muted">
						{m.daily_goal_progress({ xp: d.today, goal: settings.dailyGoal })} · {m.streak_longest({
							days: d.streak.longest
						})}
					</p>
				</div>
			</section>

			{#each packs as { course } (course.id)}
				{@const sections = [true, false]
					.map((script) => ({ script, units: section(course.units, script) }))
					.filter((s) => s.units.length)}
				{@const hasScript = course.units.some(isScript)}
				{@const vocabStarted = section(course.units, false).some(
					(u) => d.progress.get(`${course.id}/${u.id}`)?.lessons.length
				)}
				<h1 class="sr-only">{course.title ? localized(course.title, lang) : course.id}</h1>
				{#each sections as { script, units }, s (script)}
					{@const status = statuses(course.id, units, d.progress)}
					{@const tone = script ? 'purple' : 'green'}
					{@const scrollHere = script ? !vocabStarted : vocabStarted || !hasScript}
					{#if hasScript}
						<div class="mt-8 mb-2 flex items-center gap-3 text-center">
							<span class="h-0.5 flex-1 bg-line"></span>
							<div>
								<h2 class="label text-muted">{script ? m.section_hangul() : m.section_vocab()}</h2>
								{#if script}<p class="text-sm text-muted">{m.section_hangul_hint()}</p>{/if}
							</div>
							<span class="h-0.5 flex-1 bg-line"></span>
						</div>
					{/if}
					<ol class="flex flex-col" data-testid="units" data-section={script ? 'script' : 'vocab'}>
						{#each units as unit, n (unit.id)}
							{@const p = d.progress.get(`${course.id}/${unit.id}`)}
							{@const title = localized(unit.title, lang)}
							<li data-unit={unit.id} data-status={status[n]} class="pb-6">
								<div class="sticky top-14 z-[5] -mx-1 bg-bg px-1 pt-3 pb-2">
									<div
										class="flex min-h-20 flex-col justify-center rounded-card border-b-4 px-4 py-2.5 {status[
											n
										] === 'locked'
											? 'border-locked-shade bg-locked-fill text-locked-on'
											: script
												? 'border-purple-shade bg-purple-fill text-white'
												: 'border-green-shade bg-green-fill text-white'}"
										data-testid="unit-banner"
									>
										<p class="label opacity-85">
											{m.path_unit({ section: hasScript ? s + 1 : 1, unit: n + 1 })}
										</p>
										<h3 class="text-xl leading-tight font-extrabold">{title}</h3>
									</div>
								</div>
								<div class="flex flex-col gap-6 pt-14">
									{#each Array.from({ length: LESSONS_PER_UNIT }, (_, i) => i + 1) as lesson (lesson)}
										{@const kind = nodeState(status[n], p, lesson)}
										{@const id = `${unit.id}/${lesson}`}
										<LessonNode
											{kind}
											{tone}
											offset={offset(n * LESSONS_PER_UNIT + lesson - 1)}
											bind:open={() => openNode === id, (v) => (openNode = v ? id : null)}
											label={m.node_label({ lesson, unit: title })}
											{title}
											detail={kind === 'locked'
												? m.node_locked()
												: `${m.node_lesson({ lesson, total: LESSONS_PER_UNIT })} · ${
														script
															? m.unit_letters({ count: unit.items.length })
															: m.unit_words({ count: unit.items.length })
													}${kind === 'done' ? ` · ${m.unit_done()}` : ''}`}
											to={kind === 'active' || status[n] === 'done'
												? { course: course.id, unit: unit.id }
												: undefined}
											action={status[n] === 'done'
												? m.node_practice()
												: kind === 'active'
													? m.node_start()
													: undefined}
											autoscroll={scrollHere && kind === 'active'}
										/>
									{/each}
								</div>
							</li>
						{/each}
					</ol>
				{/each}
			{/each}
		{/await}
	{/snippet}
</CourseGate>

<script lang="ts">
	import { resolve } from '$app/paths';
	import Confirm from '#lib/components/Confirm.svelte';
	import Toggle from '#lib/components/Toggle.svelte';
	import { resetProgress } from '#lib/db.js';
	import { listCourses } from '#lib/pack.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, locales, setLocale } from '#lib/paraglide/runtime.js';
	import { DAILY_GOALS, settings, type Theme } from '#lib/settings.svelte.js';

	const names = { en: m.language_en, id: m.language_id };
	const themes: [Theme, () => string][] = [
		['system', m.settings_theme_system],
		['light', m.settings_theme_light],
		['dark', m.settings_theme_dark]
	];
	let courses = $state<string[]>([]);
	void listCourses().then((c) => (courses = c));
	let confirmReset = $state(false);
	let resetDone = $state(false);

	function setCourseRoman(course: string, value: string) {
		const next = { ...settings.romanizationByCourse };
		if (value === '') delete next[course];
		else next[course] = value === 'show';
		settings.romanizationByCourse = next;
	}

	const choice = 'card chip min-h-11 flex-1 px-2 font-bold whitespace-nowrap';
</script>

{#snippet group(title: string)}
	<h2 class="label mt-7 mb-2 px-1 text-muted">{title}</h2>
{/snippet}

<h1 class="pt-6 text-3xl font-black">{m.settings_title()}</h1>

{@render group(m.settings_group_language())}
<fieldset class="rounded-card border-2 border-line p-3">
	<legend class="sr-only">{m.language_label()}</legend>
	<div class="flex flex-wrap gap-2">
		{#each locales as locale (locale)}
			<button
				type="button"
				class={choice}
				aria-pressed={getLocale() === locale}
				onclick={() => setLocale(locale)}
			>
				{names[locale]()}
			</button>
		{/each}
	</div>
</fieldset>

{@render group(m.settings_group_reading())}
<div class="divide-y-2 divide-line rounded-card border-2 border-line">
	<Toggle label={m.settings_romanization()} bind:checked={settings.romanization} />
	{#each courses as course (course)}
		<label class="flex min-h-14 items-center justify-between gap-3 px-4 py-2 font-bold">
			{m.settings_romanization_course({ course })}
			<select
				class="min-h-11 rounded-chip border-2 border-line bg-bg px-2 font-bold"
				value={course in settings.romanizationByCourse
					? settings.romanizationByCourse[course]
						? 'show'
						: 'hide'
					: ''}
				onchange={(e) => setCourseRoman(course, e.currentTarget.value)}
			>
				<option value="">{m.settings_follow_global()}</option>
				<option value="show">{m.settings_show()}</option>
				<option value="hide">{m.settings_hide()}</option>
			</select>
		</label>
	{/each}
</div>

{@render group(m.settings_group_lessons())}
<div class="divide-y-2 divide-line rounded-card border-2 border-line">
	<Toggle label={m.settings_learn_script()} bind:checked={settings.learnScript} />
	<Toggle label={m.settings_autoplay()} bind:checked={settings.autoplay} />
	<fieldset class="px-4 py-3">
		<legend class="float-left mb-2 font-bold">{m.settings_daily_goal()}</legend>
		<div class="clear-both flex flex-wrap gap-2">
			{#each DAILY_GOALS as goal (goal)}
				<button
					type="button"
					class={choice}
					aria-pressed={settings.dailyGoal === goal}
					onclick={() => (settings.dailyGoal = goal)}
				>
					{goal} XP
				</button>
			{/each}
		</div>
	</fieldset>
	<fieldset class="px-4 py-3">
		<legend class="float-left mb-2 font-bold">{m.settings_week_start()}</legend>
		<div class="clear-both flex flex-wrap gap-2">
			<button
				type="button"
				class={choice}
				aria-pressed={settings.weekStart === 1}
				onclick={() => (settings.weekStart = 1)}
			>
				{m.settings_monday()}
			</button>
			<button
				type="button"
				class={choice}
				aria-pressed={settings.weekStart === 0}
				onclick={() => (settings.weekStart = 0)}
			>
				{m.settings_sunday()}
			</button>
		</div>
	</fieldset>
</div>

{@render group(m.settings_group_look())}
<fieldset class="rounded-card border-2 border-line px-4 py-3" data-testid="theme">
	<legend class="float-left mb-2 font-bold">{m.settings_theme()}</legend>
	<div class="clear-both flex flex-wrap gap-2">
		{#each themes as [value, label] (value)}
			<button
				type="button"
				class={choice}
				aria-pressed={settings.theme === value}
				onclick={() => (settings.theme = value)}
			>
				{label()}
			</button>
		{/each}
	</div>
</fieldset>

{@render group(m.settings_group_about())}
<div class="divide-y-2 divide-line rounded-card border-2 border-line">
	<a
		class="flex min-h-14 items-center justify-between px-4 font-bold hover:bg-raised"
		href={resolve('/credits')}
	>
		{m.nav_credits()}
		<span class="text-muted" aria-hidden="true">›</span>
	</a>
	<details class="group">
		<summary
			class="flex min-h-14 cursor-pointer list-none items-center justify-between px-4 font-bold hover:bg-raised"
		>
			{m.settings_advanced()}
			<span class="text-muted transition-transform group-open:rotate-90" aria-hidden="true">›</span>
		</summary>
		<div class="border-t-2 border-line">
			<Toggle label={m.settings_contributor()} bind:checked={settings.contributor} />
			<div class="px-4 pt-1 pb-4">
				<button type="button" class="btn btn-red w-full" onclick={() => (confirmReset = true)}>
					{m.settings_reset()}
				</button>
				{#if resetDone}<p role="status" class="mt-2 font-bold text-green-ink">
						{m.settings_reset_done()}
					</p>{/if}
			</div>
		</div>
	</details>
</div>
<Confirm
	bind:open={confirmReset}
	message={m.settings_reset_confirm()}
	yes={m.settings_reset_yes()}
	no={m.settings_reset_no()}
	onyes={async () => {
		await resetProgress();
		resetDone = true;
	}}
/>

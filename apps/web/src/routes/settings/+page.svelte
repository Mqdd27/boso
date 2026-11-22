<script lang="ts">
	import { resolve } from '$app/paths';
	import Confirm from '#lib/components/Confirm.svelte';
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

	const field = 'flex flex-col gap-2 border-b py-4 dark:border-zinc-800';
	const choice =
		'min-h-11 rounded-lg border px-4 aria-pressed:bg-zinc-900 aria-pressed:text-white dark:aria-pressed:bg-zinc-100 dark:aria-pressed:text-zinc-900';
</script>

<h1 class="mb-2 text-2xl font-bold">{m.settings_title()}</h1>

<fieldset class={field}>
	<legend class="mb-2 font-semibold">{m.language_label()}</legend>
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

<div class={field}>
	<label class="flex min-h-11 items-center gap-3">
		<input type="checkbox" class="size-5" bind:checked={settings.romanization} />
		{m.settings_romanization()}
	</label>
	{#each courses as course (course)}
		<label class="flex flex-col gap-1 text-sm">
			{m.settings_romanization_course({ course })}
			<select
				class="min-h-11 rounded-lg border px-2 dark:bg-zinc-900"
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

<label class="{field} flex-row items-center">
	<input type="checkbox" class="size-5" bind:checked={settings.autoplay} />
	{m.settings_autoplay()}
</label>

<fieldset class={field}>
	<legend class="mb-2 font-semibold">{m.settings_daily_goal()}</legend>
	<div class="flex flex-wrap gap-2">
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

<fieldset class={field}>
	<legend class="mb-2 font-semibold">{m.settings_week_start()}</legend>
	<div class="flex flex-wrap gap-2">
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

<fieldset class={field}>
	<legend class="mb-2 font-semibold">{m.settings_theme()}</legend>
	<div class="flex flex-wrap gap-2">
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

<details class="py-4">
	<summary class="min-h-11 cursor-pointer font-semibold">{m.settings_advanced()}</summary>
	<label class="mt-2 flex min-h-11 items-center gap-3">
		<input type="checkbox" class="size-5 shrink-0" bind:checked={settings.contributor} />
		{m.settings_contributor()}
	</label>
	<button
		type="button"
		class="mt-4 min-h-11 rounded-lg border border-red-600 px-4 text-red-700 dark:text-red-400"
		onclick={() => (confirmReset = true)}
	>
		{m.settings_reset()}
	</button>
	{#if resetDone}<p role="status" class="mt-2">{m.settings_reset_done()}</p>{/if}
</details>

<p class="py-2"><a class="underline" href={resolve('/credits')}>{m.nav_credits()}</a></p>

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

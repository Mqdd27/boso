<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale, locales, setLocale } from '#lib/paraglide/runtime.js';

	const names = { en: m.language_en, id: m.language_id };
</script>

<svelte:head>
	<title>{m.app_name()}</title>
</svelte:head>

<main class="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-6 px-4 py-8">
	<h1 class="text-5xl font-bold">{m.app_name()}</h1>
	<p class="text-lg">{m.tagline()}</p>
	<p class="text-sm opacity-70">{m.status()}</p>

	<fieldset class="flex flex-wrap items-center gap-2">
		<legend class="mb-2 text-sm font-medium">{m.language_label()}</legend>
		{#each locales as locale (locale)}
			<button
				type="button"
				class="min-h-11 rounded-lg border px-4 aria-pressed:bg-black aria-pressed:text-white"
				aria-pressed={getLocale() === locale}
				onclick={() => setLocale(locale)}
			>
				{names[locale]()}
			</button>
		{/each}
	</fieldset>
</main>

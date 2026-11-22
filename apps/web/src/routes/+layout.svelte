<script lang="ts">
	import { page } from '$app/state';
	import favicon from '#lib/assets/favicon.svg';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { loadSettings, saveSettings, settings } from '#lib/settings.svelte.js';
	import type { LayoutProps } from './$types';
	import NavBar from '#lib/components/NavBar.svelte';
	import './layout.css';

	let { children }: LayoutProps = $props();

	const ready = loadSettings();
	let loaded = $state(false);
	void ready.then(() => (loaded = true));

	$effect(() => {
		document.documentElement.lang = getLocale();
	});

	// Persist every settings change (after the initial load).
	$effect(() => {
		JSON.stringify(settings);
		if (loaded) void saveSettings();
	});

	$effect(() => {
		const media = matchMedia('(prefers-color-scheme: dark)');
		const apply = () =>
			document.documentElement.classList.toggle(
				'dark',
				settings.theme === 'dark' || (settings.theme === 'system' && media.matches)
			);
		apply();
		media.addEventListener('change', apply);
		return () => media.removeEventListener('change', apply);
	});

	const inLesson = $derived(page.url.pathname.startsWith('/learn/'));
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{m.app_name()}</title>
</svelte:head>

<div class="min-h-dvh lg:flex">
	{#if !inLesson}<NavBar />{/if}
	<main
		class="mx-auto flex min-h-dvh w-full max-w-2xl flex-col px-4 {inLesson
			? ''
			: 'pb-[calc(5.5rem+env(safe-area-inset-bottom))] lg:pb-10'}"
	>
		{#if loaded}{@render children()}{/if}
	</main>
</div>

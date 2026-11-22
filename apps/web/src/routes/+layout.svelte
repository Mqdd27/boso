<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import favicon from '#lib/assets/favicon.svg';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { loadSettings, saveSettings, settings } from '#lib/settings.svelte.js';
	import type { LayoutProps } from './$types';
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
	const nav = [
		{ href: resolve('/'), label: m.nav_home },
		{ href: resolve('/stats'), label: m.nav_stats },
		{ href: resolve('/settings'), label: m.nav_settings }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{m.app_name()}</title>
</svelte:head>

<div class="mx-auto flex min-h-dvh max-w-2xl flex-col px-4">
	{#if !inLesson}
		<header class="flex items-center justify-between gap-2 py-3">
			<a href={resolve('/')} class="text-2xl font-bold">{m.app_name()}</a>
			<nav class="flex gap-1">
				{#each nav as link (link.href)}
					<a
						href={link.href}
						class="flex min-h-11 items-center rounded-lg px-3 aria-[current=page]:bg-zinc-100 dark:aria-[current=page]:bg-zinc-800"
						aria-current={page.url.pathname === link.href ? 'page' : undefined}
					>
						{link.label()}
					</a>
				{/each}
			</nav>
		</header>
	{/if}
	<main class="flex flex-1 flex-col">
		{#if loaded}{@render children()}{/if}
	</main>
	{#if !inLesson}
		<footer class="py-6 text-center text-sm opacity-70">
			<a href={resolve('/credits')} class="inline-flex min-h-11 items-center underline">
				{m.nav_credits()}
			</a>
		</footer>
	{/if}
</div>

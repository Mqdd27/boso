<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import Icon, { type IconName } from './Icon.svelte';

	// Bottom tab bar on phones, left sidebar from 1024px. Credits live inside Settings.
	const tabs: { href: string; label: () => string; icon: IconName; also?: string[] }[] = [
		{ href: resolve('/'), label: m.nav_home, icon: 'learn' },
		{ href: resolve('/stats'), label: m.nav_stats, icon: 'stats' },
		{ href: resolve('/settings'), label: m.nav_settings, icon: 'settings', also: ['/credits'] }
	];
	const current = (t: (typeof tabs)[number]) =>
		page.url.pathname === t.href || !!t.also?.includes(page.url.pathname);
</script>

<nav
	class="fixed inset-x-0 bottom-0 z-20 border-t-2 border-line bg-bg pb-[env(safe-area-inset-bottom)] lg:sticky lg:top-0 lg:h-dvh lg:w-64 lg:shrink-0 lg:border-t-0 lg:border-r-2 lg:px-4 lg:py-6"
	aria-label={m.nav_label()}
>
	<a
		href={resolve('/')}
		class="mb-6 hidden px-4 text-3xl font-black tracking-tight text-green-ink lg:block"
	>
		{m.app_name()}
	</a>
	<ul class="mx-auto flex max-w-md justify-around px-2 py-1.5 lg:flex-col lg:gap-2 lg:p-0">
		{#each tabs as tab (tab.href)}
			<li class="flex-1">
				<a
					href={tab.href}
					aria-current={current(tab) ? 'page' : undefined}
					class="flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-xl border-2 border-transparent px-2 text-xs font-extrabold tracking-wide text-muted uppercase transition-colors hover:bg-raised aria-[current=page]:border-blue-ink aria-[current=page]:bg-blue-soft aria-[current=page]:text-blue-ink lg:flex-row lg:justify-start lg:gap-4 lg:px-4 lg:text-sm"
				>
					<Icon name={tab.icon} size={26} />
					{tab.label()}
				</a>
			</li>
		{/each}
	</ul>
</nav>

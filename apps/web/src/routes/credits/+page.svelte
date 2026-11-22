<script lang="ts">
	import CourseGate from '#lib/components/CourseGate.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { localized, type Pack } from '#lib/types.js';

	const lang = getLocale();
	const MODIFIED = ' (modified)';
</script>

<h1 class="pt-6 text-3xl font-black">{m.credits_title()}</h1>
<p class="mt-2 mb-6 text-muted">{m.credits_intro()}</p>

<CourseGate>
	{#snippet children(packs: Pack[])}
		{#each packs as { course, manifest } (course.id)}
			<section class="mb-8" data-testid="credits-{course.id}">
				<h2 class="label mb-2 px-1 text-muted">
					{course.title ? localized(course.title, lang) : course.id}
				</h2>
				<ul class="divide-y-2 divide-line rounded-card border-2 border-line">
					{#each manifest.attribution as a, n (n)}
						<li class="px-4 py-3 leading-relaxed">
							{#if a.url}<a
									class="font-extrabold text-blue-ink underline underline-offset-4"
									href={a.url}
									rel="external noopener"
								>
									{a.source}
								</a>{:else}<span class="font-extrabold">{a.source}</span>{/if}
							{#if a.authors?.length}· {a.authors.join(', ')}{/if}
							· {a.license}
							{#if a.items}· {m.credits_items({ count: a.items })}{/if}
							{#if a.source.endsWith(MODIFIED)}<br /><span class="text-sm text-muted">
									{m.credits_modified()}
								</span>{/if}
						</li>
					{/each}
				</ul>
				{#if course.units.some( (u) => u.items.some( (i) => Object.values(i.gloss_sources ?? {}).some((c) => c.source === 'boso') ) )}
					<p class="mt-3 px-1 text-muted">{m.credits_translations()}</p>
				{/if}
				{#if course.units.some((u) => u.items.some((i) => i.audio))}
					<p class="mt-2 px-1 text-muted">{m.credits_audio()}</p>
				{/if}
				<p class="mt-2 px-1 text-sm text-muted">
					{m.credits_built({ version: course.version, date: manifest.build_date.slice(0, 10) })}
				</p>
			</section>
		{/each}
	{/snippet}
</CourseGate>

<p class="mt-4 px-1 text-sm text-muted">{m.credits_app()}</p>

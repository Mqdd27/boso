<script lang="ts">
	import CourseGate from '#lib/components/CourseGate.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { localized, type Pack } from '#lib/types.js';

	const lang = getLocale();
	const MODIFIED = ' (modified)';
</script>

<h1 class="mb-4 text-2xl font-bold">{m.credits_title()}</h1>
<p class="mb-4">{m.credits_intro()}</p>

<CourseGate>
	{#snippet children(packs: Pack[])}
		{#each packs as { course, manifest } (course.id)}
			<section class="mb-6" data-testid="credits-{course.id}">
				<h2 class="mb-2 text-xl font-semibold">
					{course.title ? localized(course.title, lang) : course.id}
				</h2>
				<ul class="flex list-disc flex-col gap-2 pl-5">
					{#each manifest.attribution as a, n (n)}
						<li>
							{#if a.url}<a class="underline" href={a.url} rel="external noopener">
									{a.source}
								</a>{:else}{a.source}{/if}
							{#if a.authors?.length}· {a.authors.join(', ')}{/if}
							· {a.license}
							{#if a.items}· {m.credits_items({ count: a.items })}{/if}
							{#if a.source.endsWith(MODIFIED)}<br /><span class="text-sm opacity-80">
									{m.credits_modified()}
								</span>{/if}
						</li>
					{/each}
				</ul>
				{#if course.units.some((u) => u.items.some((i) => i.audio))}
					<p class="mt-2">{m.credits_audio()}</p>
				{/if}
				<p class="mt-2 text-sm opacity-70">
					{m.credits_built({ version: course.version, date: manifest.build_date.slice(0, 10) })}
				</p>
			</section>
		{/each}
	{/snippet}
</CourseGate>

<p class="mt-4 text-sm opacity-80">{m.credits_app()}</p>

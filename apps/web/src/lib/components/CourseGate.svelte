<script lang="ts">
	// Loads every synced course pack, or explains why there is nothing to show.
	import type { Snippet } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { listCourses, loadPack } from '#lib/pack.js';
	import type { Pack } from '#lib/types.js';

	let { children }: { children: Snippet<[Pack[]]> } = $props();

	const packs = listCourses().then((ids) => Promise.all(ids.map((id) => loadPack(id))));
</script>

{#await packs}
	<p class="py-8 text-center opacity-70">{m.loading()}</p>
{:then list}
	{#if list.length}
		{@render children(list)}
	{:else}
		<section class="py-8">
			<h1 class="mb-3 text-2xl font-bold">{m.no_course_title()}</h1>
			<p class="mb-3">{m.no_course_body()}</p>
			<pre class="overflow-x-auto rounded-xl bg-zinc-100 p-3 text-sm dark:bg-zinc-800"><code
					>cd content && uv run pipeline pack ko-en</code
				></pre>
		</section>
	{/if}
{:catch error}
	<section class="py-8" role="alert">
		<h1 class="mb-3 text-2xl font-bold">{m.pack_error_title()}</h1>
		<p class="mb-3">{m.pack_error_body()}</p>
		<pre
			class="overflow-x-auto rounded-xl bg-zinc-100 p-3 text-sm whitespace-pre-wrap dark:bg-zinc-800">{String(
				error.message ?? error
			)}</pre>
	</section>
{/await}

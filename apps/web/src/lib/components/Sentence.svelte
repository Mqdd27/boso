<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { localized, type GlossLang, type Item } from '#lib/types.js';

	// A Korean sentence; words not taught yet are dotted, tap one to see its meaning.
	let { item, lang }: { item: Item; lang: GlossLang } = $props();

	let open = $state<string | null>(null);
	const hints = $derived(new Map((item.hints ?? []).map((h) => [h.token, h.gloss])));
	const words = $derived(item.text.split(' '));
	const bare = (word: string) => word.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
</script>

<p class="flex flex-wrap justify-center gap-x-[0.3em] text-3xl leading-relaxed font-bold" lang="ko">
	{#each words as word, n (n)}
		{#if hints.has(bare(word))}
			<button
				type="button"
				class="underline decoration-dotted decoration-2 underline-offset-8"
				aria-expanded={open === bare(word)}
				aria-label={m.hint_label({ word: bare(word) })}
				data-hint={bare(word)}
				onclick={() => (open = open === bare(word) ? null : bare(word))}
			>
				{word}
			</button>
		{:else}<span>{word}</span>{/if}
	{/each}
</p>
{#if open && hints.get(open)}
	<p class="rounded-xl bg-amber-50 px-3 py-2 dark:bg-amber-950" role="status" data-testid="hint">
		<span lang="ko">{open}</span> = {localized(hints.get(open)!, lang)}
	</p>
{/if}

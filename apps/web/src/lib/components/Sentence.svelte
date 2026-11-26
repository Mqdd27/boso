<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { langOf, localized, type GlossLang, type Item } from '#lib/types.js';

	// A sentence; words not taught yet are dotted, tap one to see its meaning. Korean is split at
	// spaces, Chinese (no spaces) around the hinted words.
	let { item, lang }: { item: Item; lang: GlossLang } = $props();

	let open = $state<string | null>(null);
	const hints = $derived(new Map((item.hints ?? []).map((h) => [h.token, h.gloss])));
	const spaced = $derived(item.text.includes(' '));
	const words = $derived(
		spaced || !hints.size
			? item.text.split(' ')
			: item.text.split(new RegExp(`(${[...hints.keys()].join('|')})`)).filter(Boolean)
	);
	const bare = (word: string) => word.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
</script>

<p
	class="flex flex-wrap justify-center {spaced
		? 'gap-x-[0.3em]'
		: ''} text-3xl leading-relaxed font-bold"
	lang={langOf(item)}
>
	{#each words as word, n (n)}
		{#if hints.has(bare(word))}
			<button
				type="button"
				class="rounded-md underline decoration-muted decoration-dotted decoration-[3px] underline-offset-8 hover:bg-raised"
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
	<p
		class="rounded-card border-2 border-line bg-raised px-4 py-2 font-bold"
		role="status"
		data-testid="hint"
	>
		<span lang={langOf(item)}>{open}</span> = {localized(hints.get(open)!, lang)}
	</p>
{/if}

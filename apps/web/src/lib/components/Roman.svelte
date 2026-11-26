<script lang="ts">
	// An item's romanization. Mandarin pinyin gets a colour per tone when tone colours are on.
	import { settings } from '#lib/settings.svelte.js';
	import { syllables } from '#lib/pinyin.js';
	import type { Item } from '#lib/types.js';

	let { item }: { item: Item } = $props();

	const COLOR = ['', 'text-red-ink', 'text-orange-ink', 'text-green-ink', 'text-blue-ink', ''];
</script>

{#if item.tones && settings.toneColors}<span data-tones={item.tones}>
		{#each syllables(item.tones) as s, n (n)}<span class={COLOR[s.tone]}>{s.text}</span>{/each}
	</span>{:else}{item.roman}{/if}

<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { gloss, type GlossLang, type Item } from '#lib/types.js';
	import Badge from './Badge.svelte';

	let {
		item,
		lang,
		roman,
		onlisten
	}: { item: Item; lang: GlossLang; roman: boolean; onlisten?: () => void } = $props();
</script>

<div class="flex flex-col items-center gap-3 py-6 text-center" data-testid="intro">
	<p class="text-sm font-semibold tracking-wide uppercase opacity-70">{m.new_word()}</p>
	<p class="text-6xl font-bold" lang="ko">{item.text}</p>
	{#if roman}<p class="text-xl opacity-80" data-testid="roman">{item.roman}</p>{/if}
	<p class="text-2xl">{gloss(item, lang)}</p>
	<Badge {item} />
	{#if onlisten}
		<button type="button" class="min-h-11 rounded-xl border px-4" onclick={onlisten}>
			🔊 {m.listen()}
		</button>
	{/if}
</div>

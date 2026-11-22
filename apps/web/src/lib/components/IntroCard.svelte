<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { gloss, type GlossLang, type Item } from '#lib/types.js';
	import { SLOW } from '#lib/audio.js';
	import Badge from './Badge.svelte';
	import Icon from './Icon.svelte';

	let {
		item,
		lang,
		roman,
		onlisten
	}: { item: Item; lang: GlossLang; roman: boolean; onlisten?: (rate?: number) => void } = $props();
</script>

<div class="flex flex-col items-center gap-4 py-4 text-center" data-testid="intro">
	<p class="label rounded-full bg-purple-soft px-3 py-1 text-purple-ink">
		{item.type === 'char' ? m.new_letter() : m.new_word()}
	</p>
	<div class="card flex w-full max-w-sm flex-col items-center gap-2 px-6 py-8">
		<p class="text-7xl font-bold" lang="ko">{item.text}</p>
		{#if roman}<p class="text-xl font-bold text-muted" data-testid="roman">{item.roman}</p>{/if}
		<p class="text-2xl font-extrabold">{gloss(item, lang)}</p>
		<Badge {item} />
	</div>
	{#if onlisten}
		<div class="flex items-end gap-3">
			<button type="button" class="btn btn-blue" onclick={() => onlisten()}>
				<Icon name="speaker" />
				{m.listen()}
			</button>
			<button
				type="button"
				class="btn btn-outline size-12 !p-0 text-2xl"
				aria-label={m.listen_slow()}
				data-testid="listen-slow"
				onclick={() => onlisten(SLOW)}
			>
				🐢
			</button>
		</div>
	{/if}
</div>

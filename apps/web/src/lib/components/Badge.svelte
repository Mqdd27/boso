<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { showReview } from '#lib/settings.svelte.js';
	import type { Item } from '#lib/types.js';

	let { item }: { item: Item } = $props();
</script>

{#if item.review === 'needs_review' && showReview()}
	<span
		class="rounded-full border border-amber-500 px-2 py-0.5 text-xs text-amber-700 dark:text-amber-300"
		data-testid="unreviewed"
	>
		{m.unreviewed()}
	</span>
{/if}

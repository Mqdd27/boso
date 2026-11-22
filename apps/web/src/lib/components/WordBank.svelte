<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	// Tap cards to build the sentence; tap a placed card to put it back. Cards are tracked by
	// position, so a sentence with the same word twice works.
	let {
		bank,
		disabled,
		value = $bindable([])
	}: { bank: string[]; disabled: boolean; value?: string[] } = $props();

	let picked = $state<number[]>([]);
	$effect(() => {
		value = picked.map((n) => bank[n]);
	});

	const card =
		'min-h-11 min-w-11 rounded-xl border-2 border-zinc-300 px-3 text-lg font-semibold disabled:opacity-60 dark:border-zinc-700';
</script>

<div class="flex flex-col gap-4" data-testid="wordbank">
	<ol
		class="flex min-h-16 flex-wrap content-start gap-2 border-b-2 border-zinc-300 pb-2 dark:border-zinc-700"
		aria-label={m.arrange_answer()}
		data-testid="arranged"
	>
		{#each picked as n, at (n)}
			<li>
				<button
					type="button"
					class="{card} bg-sky-50 dark:bg-sky-950"
					lang="ko"
					{disabled}
					data-placed={bank[n]}
					onclick={() => (picked = picked.filter((_, i) => i !== at))}
				>
					{bank[n]}
				</button>
			</li>
		{/each}
	</ol>
	<ul class="flex flex-wrap justify-center gap-2" aria-label={m.arrange_bank()}>
		{#each bank as word, n (n)}
			<li>
				<button
					type="button"
					class="{card} {picked.includes(n) ? 'invisible' : ''}"
					lang="ko"
					disabled={disabled || picked.includes(n)}
					data-card={word}
					onclick={() => (picked = [...picked, n])}
				>
					{word}
				</button>
			</li>
		{/each}
	</ul>
</div>

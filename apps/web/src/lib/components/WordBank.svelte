<script lang="ts">
	import { flip } from 'svelte/animate';
	import { crossfade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { m } from '#lib/paraglide/messages.js';

	// Tap cards to build the sentence; tap a placed card to put it back. Cards are tracked by
	// position, so a sentence with the same word twice works. A card flies between the bank and the
	// answer line (FLIP via crossfade); its empty slot stays behind in the bank.
	let {
		bank,
		disabled,
		value = $bindable([])
	}: { bank: string[]; disabled: boolean; value?: string[] } = $props();

	let picked = $state<number[]>([]);
	$effect(() => {
		value = picked.map((n) => bank[n]);
	});

	const reduced =
		typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
	const [send, receive] = crossfade({ duration: reduced ? 0 : 250, easing: cubicOut });
	const card = 'card chip min-h-12 min-w-12 px-3.5 text-lg font-bold disabled:opacity-60';
</script>

<div class="flex flex-col gap-6" data-testid="wordbank">
	<ol
		class="lines flex min-h-[7.5rem] flex-wrap content-start gap-x-2 gap-y-3 pt-1"
		aria-label={m.arrange_answer()}
		data-testid="arranged"
	>
		{#each picked as n, at (n)}
			<li
				animate:flip={{ duration: reduced ? 0 : 200 }}
				in:receive={{ key: n }}
				out:send={{ key: n }}
			>
				<button
					type="button"
					class={card}
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
			<li class="relative">
				<span
					class="chip block min-h-12 min-w-12 bg-locked-fill px-3.5 py-2.5 text-lg font-bold text-transparent"
					lang="ko"
					aria-hidden="true"
				>
					{word}
				</span>
				{#if !picked.includes(n)}
					<button
						type="button"
						class="{card} absolute inset-0"
						lang="ko"
						{disabled}
						data-card={word}
						in:receive={{ key: n }}
						out:send={{ key: n }}
						onclick={() => (picked = [...picked, n])}
					>
						{word}
					</button>
				{/if}
			</li>
		{/each}
	</ul>
</div>

<style>
	/* Ruled answer lines, one per row of cards. */
	.lines {
		background-image: linear-gradient(
			to bottom,
			transparent 3.4rem,
			var(--line) 3.4rem,
			var(--line) calc(3.4rem + 2px),
			transparent calc(3.4rem + 2px)
		);
		background-size: 100% 3.75rem;
	}
</style>

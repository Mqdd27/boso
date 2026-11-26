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
		roman,
		lang,
		disabled,
		value = $bindable([])
	}: {
		bank: string[];
		roman?: string[];
		lang: string;
		disabled: boolean;
		value?: string[];
	} = $props();

	let picked = $state<number[]>([]);
	$effect(() => {
		value = picked.map((n) => bank[n]);
	});

	const reduced =
		typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
	const [send, receive] = crossfade({ duration: reduced ? 0 : 250, easing: cubicOut });
	// Cards with romanization are taller; the answer lines follow them (--row).
	const tall = $derived(!!roman?.some(Boolean));
	const size = $derived(tall ? 'min-h-16 leading-tight' : 'min-h-12');
	const card = $derived(
		`card chip flex ${size} min-w-12 flex-col items-center justify-center px-3.5 text-lg font-bold whitespace-nowrap disabled:opacity-60`
	);
</script>

{#snippet face(n: number)}
	<span {lang}>{bank[n]}</span>
	{#if roman?.[n]}<span class="text-xs font-semibold opacity-70" data-testid="roman">
			{roman[n]}
		</span>{/if}
{/snippet}

<div class="flex flex-col gap-6" data-testid="wordbank">
	<ol
		style:--row={tall ? '4rem' : '3rem'}
		class="lines flex {tall
			? 'min-h-[9.5rem]'
			: 'min-h-[7.5rem]'} flex-wrap content-start gap-x-2 gap-y-3 pt-1"
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
					{disabled}
					data-placed={bank[n]}
					onclick={() => (picked = picked.filter((_, i) => i !== at))}
				>
					{@render face(n)}
				</button>
			</li>
		{/each}
	</ol>
	<ul class="flex flex-wrap justify-center gap-2" aria-label={m.arrange_bank()}>
		{#each bank as word, n (n)}
			<li class="relative">
				<span
					class="chip flex {size} min-w-12 flex-col items-center justify-center bg-locked-fill px-3.5 py-2.5 text-lg font-bold whitespace-nowrap text-transparent"
					aria-hidden="true"
				>
					{@render face(n)}
				</span>
				{#if !picked.includes(n)}
					<button
						type="button"
						class="{card} absolute inset-0"
						{disabled}
						data-card={word}
						in:receive={{ key: n }}
						out:send={{ key: n }}
						onclick={() => (picked = [...picked, n])}
					>
						{@render face(n)}
					</button>
				{/if}
			</li>
		{/each}
	</ul>
</div>

<style>
	/* Ruled answer lines, one per row of cards. */
	.lines {
		--at: calc(var(--row) + 0.4rem);
		background-image: linear-gradient(
			to bottom,
			transparent var(--at),
			var(--line) var(--at),
			var(--line) calc(var(--at) + 2px),
			transparent calc(var(--at) + 2px)
		);
		background-size: 100% calc(var(--row) + 0.75rem);
	}
</style>

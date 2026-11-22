<script lang="ts">
	import { compose } from '#lib/hangul.js';
	import type { Tiles } from '#lib/lesson.js';
	import { m } from '#lib/paraglide/messages.js';

	// The block being built, live; `value` is set once every slot the target needs is filled.
	let {
		tiles,
		disabled,
		value = $bindable(null)
	}: { tiles: Tiles; disabled: boolean; value?: string | null } = $props();

	let picked = $state({ initial: '', vowel: '', final: '' });
	const slots = $derived(
		(['initial', 'vowel', 'final'] as const).filter((slot) => tiles[slot].length > 0)
	);
	const block = $derived(
		picked.initial && picked.vowel ? compose(picked.initial, picked.vowel, picked.final) : null
	);
	const names = { initial: m.build_initial, vowel: m.build_vowel, final: m.build_final };

	$effect(() => {
		value = slots.every((slot) => picked[slot]) ? block : null;
	});
</script>

<div class="flex flex-col gap-4" data-testid="build">
	<p
		class="mx-auto flex size-28 items-center justify-center rounded-2xl border-2 border-dashed text-6xl font-bold"
		lang="ko"
		aria-live="polite"
		data-testid="block"
	>
		{block ?? (picked.initial + picked.vowel || '?')}
	</p>
	{#each slots as slot (slot)}
		<div>
			<p class="mb-1 text-sm opacity-70">{names[slot]()}</p>
			<div class="grid grid-cols-4 gap-2">
				{#each tiles[slot] as letter (letter)}
					<button
						type="button"
						class="min-h-12 rounded-xl border-2 text-2xl font-semibold disabled:opacity-60 {picked[
							slot
						] === letter
							? 'border-sky-500 bg-sky-50 dark:bg-sky-950'
							: 'border-zinc-300 dark:border-zinc-700'}"
						lang="ko"
						{disabled}
						aria-pressed={picked[slot] === letter}
						data-tile="{slot}:{letter}"
						onclick={() => (picked[slot] = picked[slot] === letter ? '' : letter)}
					>
						{letter}
					</button>
				{/each}
			</div>
		</div>
	{/each}
</div>

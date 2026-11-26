<script lang="ts">
	import { langOf, type Item } from '#lib/types.js';
	import Roman from './Roman.svelte';

	let {
		items,
		right,
		label,
		roman,
		ondone
	}: {
		items: Item[];
		right: Item[];
		label: (item: Item) => string; // what each item is matched with: gloss, or sound in script units
		roman: boolean;
		ondone: (mistakes: Set<string>) => void;
	} = $props();

	let picked = $state<string | null>(null);
	let wrong = $state<string | null>(null);
	let matched = $state(new Set<string>());
	const mistakes: string[] = [];

	function pickRight(id: string) {
		if (!picked || matched.has(id)) return;
		if (picked === id) {
			matched = new Set([...matched, id]);
			if (matched.size === items.length) ondone(new Set(mistakes));
		} else {
			mistakes.push(picked, id);
			wrong = id;
			setTimeout(() => (wrong = null), 600);
		}
		picked = null;
	}

	const base =
		'card flex min-h-16 w-full flex-col items-center justify-center px-2 py-2 text-center font-bold disabled:opacity-35';
</script>

<div class="grid grid-cols-2 gap-3" data-testid="match">
	<ul class="flex flex-col gap-3">
		{#each items as item (item.id)}
			<li>
				<button
					type="button"
					class={base}
					disabled={matched.has(item.id)}
					aria-pressed={picked === item.id}
					data-item={item.id}
					onclick={() => (picked = item.id)}
				>
					<span class="text-xl" lang={langOf(item)}>{item.text}</span>
					{#if roman}<span class="block text-xs font-semibold opacity-75" data-testid="roman">
							<Roman {item} />
						</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
	<ul class="flex flex-col gap-3">
		{#each right as item (item.id)}
			<li>
				<button
					type="button"
					class="{base} {wrong === item.id ? 'shake' : ''}"
					disabled={matched.has(item.id)}
					data-state={wrong === item.id ? 'wrong' : matched.has(item.id) ? 'right' : undefined}
					data-gloss={item.id}
					onclick={() => pickRight(item.id)}
				>
					{label(item)}
					{#if wrong === item.id}<span class="sr-only">✗</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
</div>

<style>
	.shake {
		animation: shake 300ms;
	}
	@keyframes shake {
		25% {
			transform: translateX(-5px);
		}
		75% {
			transform: translateX(5px);
		}
	}
</style>

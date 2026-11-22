<script lang="ts">
	import { gloss, type GlossLang, type Item } from '#lib/types.js';

	let {
		items,
		right,
		lang,
		roman,
		ondone
	}: {
		items: Item[];
		right: Item[];
		lang: GlossLang;
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
		'min-h-11 w-full rounded-xl border-2 px-3 py-2 text-left disabled:opacity-40 aria-pressed:border-sky-500 aria-pressed:bg-sky-50 dark:aria-pressed:bg-sky-950';
</script>

<div class="grid grid-cols-2 gap-2" data-testid="match">
	<ul class="flex flex-col gap-2">
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
					<span class="text-lg font-semibold" lang="ko">{item.text}</span>
					{#if roman}<span class="block text-xs opacity-70" data-testid="roman">
							{item.roman}
						</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
	<ul class="flex flex-col gap-2">
		{#each right as item (item.id)}
			<li>
				<button
					type="button"
					class="{base} {wrong === item.id ? 'border-red-500' : ''}"
					disabled={matched.has(item.id)}
					data-gloss={item.id}
					onclick={() => pickRight(item.id)}
				>
					{gloss(item, lang)}
					{#if wrong === item.id}<span class="sr-only">✗</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
</div>

<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { level, weeks, type DayTotal } from '#lib/stats.js';

	let {
		totals,
		from,
		to,
		weekStart,
		locale
	}: {
		totals: Map<string, DayTotal>;
		from: string;
		to: string;
		weekStart: 0 | 1;
		locale: string;
	} = $props();

	const columns = $derived(weeks(from, to, weekStart));
	const fmt = $derived(
		new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			timeZone: 'UTC'
		})
	);
	const label = (day: string) => {
		const t = totals.get(day);
		return m.heatmap_day({
			date: fmt.format(new Date(`${day}T00:00:00Z`)),
			xp: t?.xp ?? 0,
			lessons: t?.lessons ?? 0
		});
	};

	let scroller: HTMLDivElement | undefined = $state();
	$effect(() => {
		// Mobile: start scrolled to the most recent week.
		void columns;
		if (scroller) scroller.scrollLeft = scroller.scrollWidth;
	});
</script>

<figure>
	<div bind:this={scroller} class="overflow-x-auto pb-2" data-testid="heatmap">
		<div class="heatmap" role="list" aria-label={m.heatmap_label()}>
			{#each columns as week, w (w)}
				{#each week as day, d (d)}
					{#if day}
						<span
							role="listitem"
							class="cell"
							data-level={level(totals.get(day)?.xp ?? 0)}
							data-date={day}
							title={label(day)}
							aria-label={label(day)}
						></span>
					{:else}
						<span class="cell-empty" aria-hidden="true"></span>
					{/if}
				{/each}
			{/each}
		</div>
	</div>
	<figcaption class="mt-1 flex items-center justify-end gap-1 text-xs opacity-70">
		{m.heatmap_less()}
		{#each [0, 1, 2, 3, 4] as l (l)}<span class="cell" data-level={l} aria-hidden="true"
			></span>{/each}
		{m.heatmap_more()}
	</figcaption>
</figure>

<style>
	.heatmap {
		display: grid;
		grid-template-rows: repeat(7, 12px);
		grid-auto-flow: column;
		grid-auto-columns: 12px;
		gap: 3px;
		width: max-content;
	}
	.cell,
	.cell-empty {
		display: inline-block;
		width: 12px;
		height: 12px;
		border-radius: 2px;
	}
	.cell {
		background: var(--heat-0);
		outline: 1px solid var(--heat-border);
		outline-offset: -1px;
	}
	.cell[data-level='1'] {
		background: var(--heat-1);
	}
	.cell[data-level='2'] {
		background: var(--heat-2);
	}
	.cell[data-level='3'] {
		background: var(--heat-3);
	}
	.cell[data-level='4'] {
		background: var(--heat-4);
	}
</style>

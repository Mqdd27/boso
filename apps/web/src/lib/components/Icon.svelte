<script lang="ts" module>
	// Hand-drawn 24px icon set, one stroke weight. Filled icons use the same outline as a fill.
	const PATHS = {
		check: ['M5 12.5l4.5 4.5L19 7.5'],
		x: ['M6 6l12 12M18 6L6 18'],
		lock: ['M6 11h12v9.5H6z', 'M8.5 11V8a3.5 3.5 0 0 1 7 0v3'],
		star: ['M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z'],
		bolt: ['M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z'],
		flame: [
			'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3.2.3 1.6 1.4 2.7 2.5 2.7z'
		],
		speaker: ['M4 9.5h3.5L12 5.5v13l-4.5-4H4z', 'M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11'],
		learn: ['M3.5 11L12 4l8.5 7', 'M6 9.5V20h4.5v-5.5h3V20H18V9.5'],
		stats: ['M5 20V11M12 20V5M19 20v-6'],
		settings: ['M4 7h9M19 7h1M4 17h3M13 17h7', 'M16 4.5v5M10 14.5v5'],
		clock: ['M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17z', 'M12 7.5V12l3 2'],
		target: ['M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17z', 'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z']
	} as const;
	export type IconName = keyof typeof PATHS;
</script>

<script lang="ts">
	let {
		name,
		size = 24,
		filled = false,
		class: cls = ''
	}: { name: IconName; size?: number; filled?: boolean; class?: string } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill={filled ? 'currentColor' : 'none'}
	stroke="currentColor"
	stroke-width="2.5"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
	class="shrink-0 {cls}"
>
	{#each PATHS[name] as d (d)}<path {d} />{/each}
</svg>

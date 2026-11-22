<script lang="ts">
	// A settings row with a big on/off switch (a real checkbox, so labels and forms just work).
	let { label, checked = $bindable(false) }: { label: string; checked: boolean } = $props();
</script>

<label class="flex min-h-14 cursor-pointer items-center justify-between gap-4 px-4 py-2 font-bold">
	<span>{label}</span>
	<input type="checkbox" role="switch" class="switch" bind:checked />
</label>

<style>
	.switch {
		appearance: none;
		position: relative;
		flex-shrink: 0;
		width: 3.25rem;
		height: 2rem;
		border-radius: 9999px;
		background: var(--locked-fill);
		cursor: pointer;
		transition: background-color 200ms var(--ease-out-expo);
	}
	.switch::after {
		content: '';
		position: absolute;
		top: 0.25rem;
		left: 0.25rem;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 9999px;
		background: #fff;
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.3);
		transition: translate 200ms var(--ease-out-expo);
	}
	.switch:checked {
		background: var(--green-fill);
	}
	.switch:checked::after {
		translate: 1.25rem 0;
	}
</style>

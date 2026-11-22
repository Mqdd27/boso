<script lang="ts">
	// In-page confirmation (no window.confirm: it blocks the page and is unstyled).
	let {
		open = $bindable(false),
		message,
		yes,
		no,
		onyes
	}: { open: boolean; message: string; yes: string; no: string; onyes: () => void } = $props();
</script>

{#if open}
	<div
		class="fixed inset-0 z-40 flex items-end justify-center bg-black/50 p-4 sm:items-center"
		role="presentation"
	>
		<div
			class="w-full max-w-sm rounded-card border-2 border-line bg-bg p-5 shadow-[0_12px_32px_rgb(0_0_0/0.3)]"
			role="alertdialog"
			aria-modal="true"
			aria-labelledby="confirm-message"
		>
			<p id="confirm-message" class="mb-5 text-lg font-bold">{message}</p>
			<div class="flex flex-col gap-3">
				<button
					type="button"
					class="btn btn-red"
					onclick={() => {
						open = false;
						onyes();
					}}
				>
					{yes}
				</button>
				<!-- svelte-ignore a11y_autofocus -->
				<button type="button" autofocus class="btn btn-outline" onclick={() => (open = false)}>
					{no}
				</button>
			</div>
		</div>
	</div>
{/if}

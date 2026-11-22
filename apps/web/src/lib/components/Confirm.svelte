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
		class="fixed inset-0 z-20 flex items-end justify-center bg-black/40 p-4 sm:items-center"
		role="presentation"
	>
		<div
			class="w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl dark:bg-zinc-900"
			role="alertdialog"
			aria-modal="true"
			aria-labelledby="confirm-message"
		>
			<p id="confirm-message" class="mb-4">{message}</p>
			<div class="flex flex-col gap-2 sm:flex-row-reverse">
				<button
					type="button"
					class="min-h-11 rounded-xl bg-red-600 px-4 font-semibold text-white"
					onclick={() => {
						open = false;
						onyes();
					}}
				>
					{yes}
				</button>
				<!-- svelte-ignore a11y_autofocus -->
				<button
					type="button"
					autofocus
					class="min-h-11 rounded-xl border px-4 font-semibold"
					onclick={() => (open = false)}
				>
					{no}
				</button>
			</div>
		</div>
	</div>
{/if}

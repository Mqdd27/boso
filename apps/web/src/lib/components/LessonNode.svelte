<script lang="ts">
	import { resolve } from '$app/paths';
	import { m } from '#lib/paraglide/messages.js';
	import type { NodeState } from '#lib/types.js';
	import Icon from './Icon.svelte';

	// One lesson on the path: a round 3D button, shifted sideways by `offset` px. Tapping it opens
	// a small card underneath (in the page flow, so it never overflows a narrow screen).
	let {
		kind,
		tone,
		offset,
		open = $bindable(false),
		label,
		title,
		detail,
		to,
		action,
		autoscroll = false
	}: {
		kind: NodeState;
		tone: 'purple' | 'green';
		offset: number;
		open?: boolean;
		label: string;
		title: string;
		detail: string;
		to?: { course: string; unit: string }; // where the action button goes
		action?: string;
		autoscroll?: boolean;
	} = $props();

	const face = $derived(
		kind === 'locked'
			? 'bg-locked-fill border-b-locked-shade text-locked-on'
			: kind === 'done'
				? 'bg-gold-fill border-b-gold-shade text-gold-on'
				: tone === 'purple'
					? 'bg-purple-fill border-b-purple-shade text-white'
					: 'bg-green-fill border-b-green-shade text-white'
	);
	const ring = $derived(tone === 'purple' ? 'text-purple-ink' : 'text-green-ink');
</script>

<div class="flex flex-col items-center" data-node-wrap>
	<div class="relative" style:translate="{offset}px 0">
		{#if kind === 'active'}
			<span
				class="start-tip pointer-events-none absolute -top-11 left-1/2 rounded-xl border-2 border-line bg-bg px-3 py-1.5 text-sm font-extrabold tracking-wider uppercase {ring}"
				aria-hidden="true"
			>
				{m.node_start()}
			</span>
			<span class="pulse absolute inset-0 rounded-full {ring}" aria-hidden="true"></span>
		{/if}
		<button
			type="button"
			class="node relative flex size-[4.5rem] items-center justify-center rounded-full border-b-[7px] {face}"
			aria-label={label}
			aria-expanded={open}
			data-node={kind}
			data-autoscroll={autoscroll || undefined}
			onclick={() => (open = !open)}
		>
			<Icon
				name={kind === 'locked' ? 'lock' : kind === 'done' ? 'check' : 'star'}
				size={34}
				filled={kind === 'active'}
			/>
		</button>
	</div>

	{#if open}
		<div
			class="pop relative mt-4 w-full max-w-xs rounded-card border-2 border-line bg-bg p-4 shadow-[0_8px_24px_rgb(0_0_0/0.18)]"
			style:translate="{offset / 2}px 0"
			role="group"
			aria-label={title}
			data-testid="node-pop"
		>
			<p class="text-lg font-extrabold">{title}</p>
			<p class="mb-3 text-muted">{detail}</p>
			{#if to && action}
				<a
					href={resolve('/learn/[course]/[unit]', to)}
					class="btn w-full {tone === 'purple' && kind === 'active' ? 'btn-purple' : ''} {kind ===
					'done'
						? 'btn-gold'
						: ''}"
				>
					{action}
				</a>
			{/if}
		</div>
	{/if}
</div>

<style>
	.node {
		transition: transform 100ms var(--ease-out-expo);
	}
	.node:active {
		transform: translateY(4px);
		border-bottom-width: 3px;
		margin-top: 4px;
	}
	.pulse {
		animation: pulse 2s var(--ease-out-expo) infinite;
		border: 4px solid currentColor;
		opacity: 0;
	}
	@keyframes pulse {
		0% {
			transform: scale(0.95);
			opacity: 0.6;
		}
		100% {
			transform: scale(1.45);
			opacity: 0;
		}
	}
	.start-tip {
		translate: -50% 0;
		animation: bob 1.6s ease-in-out infinite;
	}
	.start-tip::after {
		content: '';
		position: absolute;
		left: 50%;
		bottom: -7px;
		width: 12px;
		height: 12px;
		translate: -50% 0;
		rotate: 45deg;
		background: var(--bg);
		border-right: 2px solid var(--line);
		border-bottom: 2px solid var(--line);
	}
	@keyframes bob {
		50% {
			transform: translateY(-4px);
		}
	}
	.pop {
		animation: pop 200ms var(--ease-out-expo);
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: translateY(-6px) scale(0.97);
		}
	}
</style>

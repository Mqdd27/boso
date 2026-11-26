<script lang="ts">
	import { enter, logout, me, type AccountState } from '#lib/account.js';
	import { m } from '#lib/paraglide/messages.js';

	let account = $state<AccountState | 'loading'>('loading');
	let email = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	void me().then((s) => (account = s));

	const errors: Record<string, () => string> = {
		invalid_email: m.account_err_invalid_email,
		weak_password: m.account_err_weak_password,
		email_taken: m.account_err_email_taken,
		wrong_login: m.account_err_wrong_login
	};

	async function submit(mode: 'login' | 'signup') {
		busy = true;
		error = '';
		const r = await enter(mode, email.trim(), password);
		busy = false;
		if ('error' in r) error = (errors[r.error] ?? m.account_err_other)();
		else {
			account = r;
			password = '';
		}
	}

	const field = 'min-h-11 w-full rounded-chip border-2 border-line bg-bg px-3 font-bold';
</script>

<div class="rounded-card border-2 border-line p-4" data-testid="account">
	{#if account === 'loading'}
		<p class="text-muted">…</p>
	{:else if account === 'unavailable'}
		<p class="text-muted" data-testid="account-unavailable">{m.account_unavailable()}</p>
	{:else if account}
		<p class="font-bold" data-testid="account-email">
			{m.account_logged_in({ email: account.email })}
		</p>
		<button
			type="button"
			class="btn btn-outline mt-3 w-full"
			onclick={async () => {
				await logout();
				account = null;
			}}
		>
			{m.account_logout()}
		</button>
	{:else}
		<form
			class="flex flex-col gap-3"
			onsubmit={(e) => {
				e.preventDefault();
				void submit('login');
			}}
		>
			<p class="text-sm text-muted">{m.account_why()}</p>
			<label class="flex flex-col gap-1 font-bold">
				{m.account_email()}
				<input class={field} type="email" autocomplete="email" required bind:value={email} />
			</label>
			<label class="flex flex-col gap-1 font-bold">
				{m.account_password()}
				<input
					class={field}
					type="password"
					autocomplete="current-password"
					required
					minlength={8}
					bind:value={password}
				/>
			</label>
			{#if error}<p role="alert" class="font-bold text-red-ink">{error}</p>{/if}
			<div class="flex gap-3">
				<button type="submit" class="btn btn-blue flex-1" disabled={busy}>
					{m.account_login()}
				</button>
				<button
					type="button"
					class="btn btn-outline flex-1"
					disabled={busy}
					onclick={(e) => {
						if (e.currentTarget.form?.reportValidity()) void submit('signup');
					}}
				>
					{m.account_signup()}
				</button>
			</div>
		</form>
	{/if}
</div>

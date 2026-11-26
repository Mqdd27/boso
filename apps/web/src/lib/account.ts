// Account API client (the Go server's /api). Accounts are optional: without a server (a static
// deploy, offline) the app keeps working locally and the account section says so.

export type Me = { email: string };
/** null = logged out; 'unavailable' = no boso server answers /api. */
export type AccountState = Me | null | 'unavailable';

const json = { 'Content-Type': 'application/json' };

/** A server answer is JSON; a static host's SPA fallback (index.html) or 404 is not a server. */
async function body(res: Response): Promise<Record<string, string> | undefined> {
	if (!res.headers.get('Content-Type')?.includes('application/json')) return undefined;
	return (await res.json()) as Record<string, string>;
}

export async function me(): Promise<AccountState> {
	try {
		const res = await fetch('/api/me', { credentials: 'same-origin' });
		const data = await body(res);
		if (!data || res.status >= 500) return 'unavailable';
		return res.ok ? { email: data.email } : null;
	} catch {
		return 'unavailable';
	}
}

/** Log in or sign up. Returns the user, or an error code (see account_err_* messages). */
export async function enter(
	mode: 'login' | 'signup',
	email: string,
	password: string
): Promise<Me | { error: string }> {
	try {
		const res = await fetch(`/api/${mode}`, {
			method: 'POST',
			headers: json,
			credentials: 'same-origin',
			body: JSON.stringify({ email, password })
		});
		const data = await body(res);
		if (res.ok && data) return { email: data.email };
		return { error: data?.error ?? 'other' };
	} catch {
		return { error: 'other' };
	}
}

export async function logout(): Promise<void> {
	await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {});
}

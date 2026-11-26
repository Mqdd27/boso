import { expect, test, type Page } from '@playwright/test';
import { mockSpeech, playLesson } from './helpers';

type Doc = { kind: string; id: string; v: string; data: unknown; seq?: number };

/** A fake /api with one user (ana@example.com / hunter22!) and the server's sync rules
 *  (larger v wins, changes pulled by seq). Pass the same `docs` to two pages = two devices. */
async function fakeServer(page: Page, docs = new Map<string, Doc>()) {
	let user: string | null = null;
	let seq = Math.max(0, ...[...docs.values()].map((d) => d.seq ?? 0));
	await page.route('**/api/**', async (route) => {
		const req = route.request();
		const path = new URL(req.url()).pathname;
		const send = (status: number, body: object) => route.fulfill({ status, json: body });
		if (path === '/api/me') return user ? send(200, { email: user }) : send(401, { error: 'x' });
		if (path === '/api/logout') {
			user = null;
			return route.fulfill({ status: 204 });
		}
		if (path === '/api/sync') {
			if (!user) return send(401, { error: 'not_logged_in' });
			const body = req.postDataJSON() as { since: number; docs: Doc[] };
			for (const d of body.docs) {
				const k = `${d.kind}/${d.id}`;
				if (!docs.has(k) || d.v > docs.get(k)!.v) docs.set(k, { ...d, seq: ++seq });
			}
			const changed = [...docs.values()].filter((d) => d.seq! > body.since);
			return send(200, { docs: changed, cursor: Math.max(body.since, seq), more: false });
		}
		const { email, password } = req.postDataJSON() as { email: string; password: string };
		if (path === '/api/signup')
			return email === 'ana@example.com'
				? send(409, { error: 'email_taken' })
				: send(201, { email: (user = email) });
		if (email === 'ana@example.com' && password === 'hunter22!')
			return send(200, { email: (user = email) });
		return send(401, { error: 'wrong_login' });
	});
}

async function logIn(page: Page) {
	await page.goto('/settings');
	const account = page.getByTestId('account');
	await account.getByLabel('Email').fill('ana@example.com');
	await account.getByLabel('Password').fill('hunter22!');
	await account.getByRole('button', { name: 'Log in' }).click();
	await expect(page.getByTestId('account-synced')).toBeVisible();
}

test('log in, see the account, log out', async ({ page }) => {
	await fakeServer(page);
	await page.goto('/settings');
	const account = page.getByTestId('account');
	await account.getByLabel('Email').fill('ana@example.com');
	await account.getByLabel('Password').fill('wrong-pass');
	await account.getByRole('button', { name: 'Log in' }).click();
	await expect(account.getByRole('alert')).toHaveText('Wrong email or password.');

	await account.getByLabel('Password').fill('hunter22!');
	await account.getByRole('button', { name: 'Create account' }).click();
	await expect(account.getByRole('alert')).toContainText('already an account');
	await account.getByRole('button', { name: 'Log in' }).click();
	await expect(page.getByTestId('account-email')).toHaveText('Logged in as ana@example.com');

	await page.reload();
	await expect(page.getByTestId('account-email')).toBeVisible();
	await page.getByRole('button', { name: 'Log out' }).click();
	await expect(account.getByLabel('Email')).toBeVisible();
});

test('without a server the app says progress stays on this device', async ({ page }) => {
	// A static host: /api answers with the SPA's index.html (not JSON).
	await page.route('**/api/**', (r) =>
		r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html>' })
	);
	await page.goto('/settings');
	await expect(page.getByTestId('account-unavailable')).toBeVisible();
});

test('progress made on one device shows up on another', async ({ browser }) => {
	const docs = new Map<string, Doc>();
	const phone = await (await browser.newContext()).newPage();
	await mockSpeech(phone);
	await fakeServer(phone, docs);
	await logIn(phone);
	await phone.goto('/learn/ko-en/ko-010-greetings');
	await playLesson(phone);
	await phone.goto('/');
	const xp = await phone.getByTestId('xp-today').textContent();
	expect(xp).not.toMatch(/^0 XP/);
	await expect.poll(() => [...docs.values()].filter((d) => d.kind === 'activity').length).toBe(1);

	const laptop = await (await browser.newContext()).newPage();
	await fakeServer(laptop, docs);
	await laptop.goto('/');
	await expect(laptop.getByTestId('xp-today')).toHaveText(/^0 XP/);
	await logIn(laptop);
	await laptop.goto('/');
	await expect(laptop.getByTestId('xp-today')).toHaveText(xp!);
});

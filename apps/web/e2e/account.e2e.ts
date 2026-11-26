import { expect, test, type Page } from '@playwright/test';

/** A fake /api with one user (ana@example.com / hunter22!). */
async function fakeServer(page: Page) {
	let user: string | null = null;
	await page.route('**/api/**', async (route) => {
		const req = route.request();
		const path = new URL(req.url()).pathname;
		const send = (status: number, body: object) => route.fulfill({ status, json: body });
		if (path === '/api/me') return user ? send(200, { email: user }) : send(401, { error: 'x' });
		if (path === '/api/logout') {
			user = null;
			return route.fulfill({ status: 204 });
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
	await page.goto('/settings'); // vite preview: /api is not a server
	await expect(page.getByTestId('account-unavailable')).toBeVisible();
});

import { expect, test } from '@playwright/test';

test('placeholder page renders and switches language', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('boso');
	await expect(page.getByText('Learn Korean and Mandarin')).toBeVisible();

	await page.getByRole('button', { name: 'Bahasa Indonesia' }).click();
	await expect(page.getByText('Belajar bahasa Korea dan Mandarin')).toBeVisible();
	await expect(page.locator('html')).toHaveAttribute('lang', 'id');
});

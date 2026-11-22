import { expect, test } from '@playwright/test';
import { mockSpeech, playLesson } from './helpers';

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
});

test('finish the first unit → next unit opens → heatmap shows today', async ({ page }) => {
	await page.goto('/');
	const first = page.locator('[data-unit="ko-010-greetings"]');
	const second = page.locator('[data-unit="ko-011-family"]');
	await expect(first).toHaveAttribute('data-status', 'open');
	await expect(second).toHaveAttribute('data-status', 'locked');

	await first.getByRole('link').click();
	await playLesson(page);
	await expect(page.getByText('+15 XP')).toBeVisible();
	await page.getByRole('button', { name: 'Next lesson' }).click();
	await playLesson(page);
	await page.getByTestId('back-home').click();

	await expect(first).toHaveAttribute('data-status', 'done');
	await expect(second).toHaveAttribute('data-status', 'open');
	await expect(page.getByTestId('xp-today')).toHaveText('30 XP today');

	await page.getByRole('link', { name: 'Stats' }).click();
	await expect(page.getByTestId('year-xp')).toHaveText('30 XP in the last year');
	const today = await page.evaluate(() => new Date().toLocaleDateString('en-CA'));
	const cell = page.locator(`[data-date="${today}"]`);
	await expect(cell).toHaveAttribute('data-level', '3');
	await expect(cell).toHaveAttribute('aria-label', /: 30 XP, 2 lessons$/);
});

test('a wrong answer shows the correct one and comes back later', async ({ page }) => {
	await page.goto('/learn/ko-en/ko-010-greetings');
	await page.getByRole('button', { name: 'Continue' }).click(); // intro card
	const ex = page.getByTestId('exercise');
	await expect(ex).toHaveAttribute('data-kind', 'meaning');
	const bar = page.getByRole('progressbar');
	const total = Number(await bar.getAttribute('aria-valuemax'));
	const text = await page.getByTestId('prompt').locator('[lang="ko"]').innerText();
	// pick a wrong option (the prompt word is 안녕 = hello)
	expect(text).toBe('안녕');
	await ex.locator('[data-option]:not([data-option="ko.w.annyeong"])').first().click();
	await page.keyboard.press('Enter');
	await expect(page.getByTestId('feedback')).toHaveAttribute('data-correct', 'false');
	await expect(page.getByTestId('feedback')).toContainText('안녕');
	await expect(bar).toHaveAttribute('aria-valuemax', String(total + 1));
});

test('romanization toggle hides romanization', async ({ page }) => {
	await page.goto('/learn/ko-en/ko-010-greetings');
	await expect(page.getByTestId('roman').first()).toBeVisible();
	await page.goto('/settings');
	await page.getByLabel('Show romanization').uncheck();
	// In-app navigation (a reload could beat the IndexedDB save).
	await page.getByRole('link', { name: 'Learn' }).click();
	await page.locator('[data-unit="ko-010-greetings"] a').click();
	await expect(page.getByTestId('intro')).toBeVisible();
	await expect(page.getByTestId('roman')).toHaveCount(0);
});

test('Indonesian UI shows Indonesian glosses', async ({ page }) => {
	await page.goto('/settings');
	await page.getByRole('button', { name: 'Bahasa Indonesia' }).click();
	await expect(page.getByRole('heading', { name: 'Pengaturan' })).toBeVisible();
	await expect(page.locator('html')).toHaveAttribute('lang', 'id');
	await page.goto('/learn/ko-en/ko-010-greetings');
	await expect(page.getByTestId('intro')).toContainText('halo');
	await expect(page.getByText('Kata baru')).toBeVisible();
});

test('unreviewed badge is hidden by default and shown in contributor mode', async ({ page }) => {
	await page.goto('/learn/ko-en/ko-010-greetings');
	await expect(page.getByTestId('intro')).toBeVisible();
	await expect(page.getByTestId('unreviewed')).toHaveCount(0);
	await page.goto('/settings');
	await page.getByText('Advanced').click();
	await page.getByLabel(/Contributor mode/).check();
	await page.getByRole('link', { name: 'Learn' }).click();
	await page.locator('[data-unit="ko-010-greetings"] a').click();
	await expect(page.getByTestId('unreviewed')).toBeVisible(); // 안녕 is needs_review
});

test('credits list the sources from the manifest', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('link', { name: 'Credits' }).click();
	const credits = page.getByTestId('credits-ko-en');
	await expect(credits).toContainText('CC BY-SA 2.0 KR');
	await expect(credits).toContainText('국립국어원');
	await expect(credits).toContainText('Some glosses were corrected');
});

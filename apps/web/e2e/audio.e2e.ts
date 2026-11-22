import { expect, test, type Page } from '@playwright/test';
import { mockSpeech } from './helpers';

type Played = { src: string; rate: number };
const played = (page: Page) =>
	page.evaluate(() => (window as unknown as { __played: Played[] }).__played);
const spoken = (page: Page) =>
	page.evaluate(() => (window as unknown as { __spoken: string[] }).__spoken);

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
});

test('plays the pack audio file, and slowly with the turtle button', async ({ page }) => {
	await page.goto('/learn/ko-en/ko-010-greetings');
	await expect(page.getByTestId('intro')).toContainText('안녕'); // first word, has a file
	await expect
		.poll(() => played(page))
		.toEqual([{ src: '/packs/ko-en/audio/ko/w.annyeong.opus', rate: 1 }]);
	await page.getByTestId('listen-slow').click();
	await expect.poll(async () => (await played(page)).at(-1)?.rate).toBe(0.7);
	expect(await spoken(page)).toEqual([]);
});

test('falls back to speech when the audio file is missing', async ({ page }) => {
	await page.route('**/audio/**', (route) => route.fulfill({ status: 404 }));
	await page.goto('/learn/ko-en/ko-010-greetings');
	await expect(page.getByTestId('intro')).toContainText('안녕');
	await expect.poll(() => spoken(page)).toEqual(['안녕']);
	expect(await played(page)).toEqual([]);
});

test('autoplay can be turned off', async ({ page }) => {
	await page.goto('/settings');
	await page.getByLabel('Play audio automatically').uncheck();
	await page.getByRole('link', { name: 'Learn' }).click();
	await page.locator('[data-unit="ko-010-greetings"] a').click();
	await expect(page.getByTestId('intro')).toBeVisible();
	await page.waitForTimeout(300);
	expect(await played(page)).toEqual([]);
	await page.getByRole('button', { name: /^🔊/ }).click();
	await expect.poll(async () => (await played(page)).length).toBe(1);
});

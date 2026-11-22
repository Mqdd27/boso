import { test, type Page } from '@playwright/test';
import { choiceAnswer, mockSpeech, openUnit, playLesson, skipToChoice } from './helpers';

// A short settle: the first frame after a click can still be the old one.
async function shot(page: Page, name: string) {
	await page.waitForTimeout(300);
	await page.screenshot({ path: `shots/${test.info().project.name}-${name}.png` });
}

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
	await page.emulateMedia({ reducedMotion: 'reduce' });
});

test('screens', async ({ page }) => {
	await page.goto('/');
	await page.locator('[data-node="active"]').first().waitFor();
	await shot(page, 'home');

	await openUnit(page, 'ko-010-greetings');
	await skipToChoice(page);
	let right = await choiceAnswer(page);
	await page.locator(`[data-option]:not([data-option="${right}"])`).first().click();
	await shot(page, 'lesson-before');
	await page.getByRole('button', { name: 'Check' }).click();
	await page.getByTestId('feedback').waitFor();
	await shot(page, 'lesson-wrong');
	await page.getByRole('button', { name: 'Continue' }).click();

	await skipToChoice(page);
	right = await choiceAnswer(page);
	await page.locator(`[data-option="${right}"]`).click();
	await page.getByRole('button', { name: 'Check' }).click();
	await page.getByTestId('feedback').waitFor();
	await shot(page, 'lesson-right');
	await page.getByRole('button', { name: 'Continue' }).click();

	await playLesson(page);
	await shot(page, 'lesson-done');

	await page.getByTestId('back-home').click();
	await page.getByRole('link', { name: 'Stats' }).click();
	await page.getByTestId('year-xp').waitFor();
	await shot(page, 'stats');
	await page.getByRole('link', { name: 'Settings' }).click();
	await page.getByRole('heading', { name: 'Settings' }).waitFor();
	await shot(page, 'settings');
});

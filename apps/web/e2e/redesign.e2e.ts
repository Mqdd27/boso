import { expect, test } from '@playwright/test';
import { choiceAnswer, mockSpeech, openUnit, showUnit, skipToChoice } from './helpers';

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
});

test('home path shows the active lesson node with a start tip', async ({ page }) => {
	await page.goto('/');
	// The lesson to play next is scrolled into view and carries the start tip.
	const next = page.locator('[data-autoscroll]');
	await expect(next).toHaveAttribute('data-node', 'active');
	await expect(next).toBeInViewport();
	await expect(page.locator('[data-node-wrap]', { has: next })).toContainText('Start');
	const unit = await showUnit(page, 'ko-010-greetings');
	await expect(unit.locator('[data-node="active"]')).toHaveCount(1);
	await expect(page.locator('[data-unit="ko-011-family"] [data-node="locked"]')).toHaveCount(2);
});

test('the feedback sheet slides up after Check', async ({ page }) => {
	await page.goto('/');
	await openUnit(page, 'ko-010-greetings');
	await skipToChoice(page);
	const check = page.getByRole('button', { name: 'Check' });
	await expect(check).toBeDisabled();
	const right = await choiceAnswer(page);
	await page.locator(`[data-option]:not([data-option="${right}"])`).first().click();
	await check.click();
	const sheet = page.getByTestId('feedback');
	await expect(sheet).toHaveAttribute('data-correct', 'false');
	await expect(sheet).toBeInViewport();
	await expect(sheet).toContainText('Correct answer:');
	await expect(page.locator(`[data-option="${right}"]`)).toHaveAttribute('data-state', 'right');
	await expect(page.getByRole('button', { name: 'Continue' })).toBeVisible();
});

test('the theme choice survives a reload', async ({ page }) => {
	await page.goto('/settings');
	await page.getByRole('button', { name: 'Dark' }).click();
	await expect(page.locator('html')).toHaveClass(/dark/);
	// In-app navigation first (a reload could beat the IndexedDB save).
	await page.getByRole('link', { name: 'Stats' }).click();
	await page.reload();
	await expect(page.locator('html')).toHaveClass(/dark/);
	await page.getByRole('link', { name: 'Settings' }).click();
	await page.getByRole('button', { name: 'Light' }).click();
	await page.getByRole('link', { name: 'Stats' }).click();
	await page.reload();
	await expect(page.locator('html')).not.toHaveClass(/dark/);
});

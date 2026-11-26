import { expect, test, type Page } from '@playwright/test';
import { buildSyllable, course, mockSpeech, playLesson, openUnit } from './helpers';

const unit = (page: Page, id: string) => page.locator(`[data-unit="${id}"]`);

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
});

test('home has separate Hangul and vocabulary paths that unlock separately', async ({ page }) => {
	await page.goto('/');
	// A new learner starts on the Hangul path; vocabulary is one tap away.
	await expect(page.locator('[data-path="script"]')).toHaveAttribute('aria-pressed', 'true');
	await expect(unit(page, 'ko-001-basic-vowels')).toHaveAttribute('data-status', 'open');
	await expect(unit(page, 'ko-002-basic-consonants-1')).toHaveAttribute('data-status', 'locked');
	await expect(unit(page, 'ko-010-greetings')).toHaveCount(0);
	await page.locator('[data-path="vocab"]').click();
	await expect(unit(page, 'ko-001-basic-vowels')).toHaveCount(0);
	// Vocabulary does not wait for Hangul.
	await expect(unit(page, 'ko-010-greetings')).toHaveAttribute('data-status', 'open');
	await openUnit(page, 'ko-010-greetings');
	await expect(page.getByTestId('exercise')).toBeVisible();
});

test('the Hangul path can be turned off in Settings', async ({ page }) => {
	await page.goto('/settings');
	await page.getByLabel('Show the Hangul (alphabet) path').uncheck();
	await page.getByRole('link', { name: 'Learn' }).click();
	await expect(unit(page, 'ko-010-greetings')).toHaveAttribute('data-status', 'open');
	await expect(page.locator('[data-path]')).toHaveCount(0);
	await expect(unit(page, 'ko-001-basic-vowels')).toHaveCount(0);
});

test('finish unit 001 → unit 002 opens', async ({ page }) => {
	await page.goto('/');
	await openUnit(page, 'ko-001-basic-vowels');
	// Intro card of a letter: sound always shown, explanation, listen buttons.
	await expect(page.getByText('New letter')).toBeVisible();
	await expect(page.getByTestId('intro').getByTestId('roman')).toHaveText('a');
	await expect(page.getByTestId('listen-slow')).toBeVisible();
	await playLesson(page);
	await page.getByRole('button', { name: 'Next lesson' }).click();
	await playLesson(page);
	await page.getByTestId('back-home').click();
	await expect(unit(page, 'ko-001-basic-vowels')).toHaveAttribute('data-status', 'done');
	await expect(unit(page, 'ko-002-basic-consonants-1')).toHaveAttribute('data-status', 'open');
});

test('build a syllable from letter tiles', async ({ page }) => {
	await page.goto('/');
	await expect(unit(page, 'ko-001-basic-vowels')).toBeVisible();
	// Units 001 and 002 already done.
	await page.evaluate(
		(units) =>
			new Promise<void>((done, fail) => {
				const open = indexedDB.open('boso');
				open.onsuccess = () => {
					const tx = open.result.transaction('unitProgress', 'readwrite');
					for (const unit of units)
						tx.objectStore('unitProgress').put({
							course: 'ko-en',
							unit,
							lessons: [1, 2],
							completedAt: new Date().toISOString()
						});
					tx.oncomplete = () => done();
					tx.onerror = () => fail(new Error(String(tx.error)));
				};
			}),
		['ko-001-basic-vowels', 'ko-002-basic-consonants-1']
	);
	await page.goto('/learn/ko-en/ko-004-syllable-blocks');
	await page.getByRole('button', { name: 'Continue' }).click(); // intro card
	const ex = page.getByTestId('exercise');
	await expect(ex).toHaveAttribute('data-kind', 'build');
	const block = course.units.find((u) => u.id === 'ko-004-syllable-blocks')!.items[0].text;
	await expect(page.getByTestId('block')).toHaveText('?');
	await buildSyllable(page, block);
	await page.getByRole('button', { name: 'Check' }).click();
	await expect(page.getByTestId('feedback')).toHaveAttribute('data-correct', 'true');
});

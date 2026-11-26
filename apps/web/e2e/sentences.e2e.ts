import { expect, test, type Page } from '@playwright/test';
import { arrange, asked, mockSpeech, playLesson, showUnit } from './helpers';

const UNIT = 'ko-010-greetings';

/** Lesson 1 of the greetings unit done, so the unit opens on lesson 2 (with sentences). */
async function lessonTwo(page: Page) {
	await page.goto('/');
	await showUnit(page, UNIT); // the app has opened the DB
	await page.evaluate(
		(unit) =>
			new Promise<void>((done, fail) => {
				const open = indexedDB.open('boso');
				open.onsuccess = () => {
					const tx = open.result.transaction('unitProgress', 'readwrite');
					tx.objectStore('unitProgress').put({ course: 'ko-en', unit, lessons: [1] });
					tx.oncomplete = () => done();
					tx.onerror = () => fail(new Error(String(tx.error)));
				};
			}),
		UNIT
	);
	await page.goto(`/learn/ko-en/${UNIT}`);
}

/** Skip ahead (answering correctly) to the first exercise matching `selector`. */
async function skipTo(page: Page, selector: string) {
	const ex = page.getByTestId('exercise');
	for (let n = 0; n < 40; n++) {
		await expect(ex).toBeVisible();
		if (await page.locator(`[data-testid="exercise"]${selector}`).count()) return;
		const step = await ex.getAttribute('data-step');
		await playLesson(page, 1);
		await expect(ex).not.toHaveAttribute('data-step', step!);
	}
	throw new Error(`no ${selector} exercise`);
}

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
});

test('arrange a sentence from the word bank (cards go back on tap)', async ({ page }) => {
	await lessonTwo(page);
	await skipTo(page, '[data-kind="arrange"][data-listen="false"]');
	const item = await asked(page);
	const bank = page.getByTestId('wordbank');
	// Decoys are in the bank too; a placed card goes back when tapped.
	expect(await bank.locator('[data-card]').count()).toBeGreaterThan(item.tokens!.length);
	await bank.locator(`[data-card="${item.tokens![1]}"]`).first().click();
	await page.locator(`[data-placed="${item.tokens![1]}"]`).click();
	await expect(page.locator('[data-placed]')).toHaveCount(0);
	await arrange(page, item);
	await page.getByRole('button', { name: 'Check' }).click();
	await expect(page.getByTestId('feedback')).toHaveAttribute('data-correct', 'true');
});

test('listen to a sentence and arrange it, then finish the lesson', async ({ page }) => {
	await lessonTwo(page);
	await skipTo(page, '[data-kind="arrange"][data-listen="true"]');
	const item = await asked(page);
	expect(item.type).toBe('sentence');
	await arrange(page, item);
	await page.getByRole('button', { name: 'Check' }).click();
	await expect(page.getByTestId('feedback')).toHaveAttribute('data-correct', 'true');
	// Listening is the last sentence exercise, so the lesson ends here.
	await page.getByRole('button', { name: /^Continue$/ }).click();
	await expect(page.getByTestId('lesson-done')).toBeVisible();
});

test('credits list Tatoeba authors and boso translations', async ({ page }) => {
	await page.goto('/credits');
	const credits = page.getByTestId('credits-ko-en');
	await expect(credits.getByRole('link', { name: 'tatoeba' })).toBeVisible();
	await expect(credits).toContainText('fixture_en, fixture_ko');
	await expect(credits).toContainText('made for this course');
});

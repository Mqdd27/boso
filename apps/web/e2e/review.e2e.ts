import { expect, test } from '@playwright/test';
import { mockSpeech, playLesson } from './helpers';

test.beforeEach(async ({ page }) => {
	await mockSpeech(page);
});

test('a finished lesson schedules its words; due words come back in a review', async ({ page }) => {
	await page.goto('/learn/ko-en/ko-010-greetings');
	await playLesson(page);
	await page.getByTestId('back-home').click();
	// Scheduled for tomorrow or later: nothing to review yet.
	await expect(page.getByTestId('summary')).toBeVisible();
	await expect(page.getByTestId('review')).toHaveCount(0);

	// A day later (move every card's due date into the past).
	await page.evaluate(
		() =>
			new Promise<void>((done) => {
				const open = indexedDB.open('boso');
				open.onsuccess = () => {
					const tx = open.result.transaction('cards', 'readwrite');
					const cards = tx.objectStore('cards');
					cards.getAll().onsuccess = (e) => {
						for (const c of (e.target as IDBRequest<{ due: number }[]>).result)
							cards.put({ ...c, due: 0 });
					};
					tx.oncomplete = () => {
						open.result.close();
						done();
					};
				};
			})
	);
	await page.reload();
	const review = page.getByTestId('review');
	await expect(review).toHaveText(/Review · \d+ due/);
	await review.click();
	await expect(page.getByText('Review', { exact: true })).toBeVisible();
	await playLesson(page);
	await page.getByTestId('back-home').click();
	await expect(page.getByTestId('review')).toHaveCount(0);

	await page.goto('/learn/ko-en/review');
	await expect(page.getByTestId('review-none')).toBeVisible();
});

import { expect, type Page } from '@playwright/test';
import pack from '../testdata/packs/ko-en/course.json' with { type: 'json' };

export const items = pack.units.flatMap((u) => u.items);

/** A fake Korean voice that records what was spoken (window.__spoken). */
export async function mockSpeech(page: Page) {
	await page.addInitScript(() => {
		const w = window as unknown as Record<string, unknown> & { __spoken: string[] };
		w.__spoken = [];
		class Utterance {
			text: string;
			voice: unknown = null;
			lang = '';
			rate = 1;
			constructor(text: string) {
				this.text = text;
			}
		}
		const voice = { lang: 'ko-KR', name: 'Mock Korean', default: true, localService: true };
		Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: Utterance });
		Object.defineProperty(window, 'speechSynthesis', {
			value: {
				getVoices: () => [voice],
				speak: (u: Utterance) => w.__spoken.push(u.text),
				cancel: () => {},
				addEventListener: () => {}
			}
		});
	});
}

/** Answer every exercise of the current lesson correctly, until the end screen. */
export async function playLesson(page: Page) {
	const done = page.getByTestId('lesson-done');
	const ex = page.getByTestId('exercise');
	let step = '';
	for (let n = 0; n < 60; n++) {
		// Wait for the next exercise (or the end screen) before reading it.
		await expect(done.or(ex.and(page.locator(`:not([data-step="${step}"])`)))).toBeVisible();
		if (await done.isVisible()) return;
		step = (await ex.getAttribute('data-step')) ?? '';
		const kind = await ex.getAttribute('data-kind');
		if (kind === 'intro') {
			await page.getByRole('button', { name: /Continue|Lanjut/ }).click();
			continue;
		}
		if (kind === 'match') {
			for (const button of await ex.locator('[data-item]').all()) {
				const id = await button.getAttribute('data-item');
				await button.click();
				await ex.locator(`[data-gloss="${id}"]`).click();
			}
		} else {
			const prompt = page.getByTestId('prompt');
			let answer: string | undefined;
			if (kind === 'meaning') {
				const text = await prompt.locator('[lang="ko"]').innerText();
				answer = items.find((i) => i.text === text)?.id;
			} else if (kind === 'listen') {
				const spoken = await page.evaluate(() =>
					(window as never as { __spoken: string[] }).__spoken.at(-1)
				);
				answer = items.find((i) => i.text === spoken)?.id;
			} else {
				// word: the prompt is a gloss; exactly one option has it
				const shown = (await prompt.locator('p').first().innerText()).trim();
				for (const option of await ex.locator('[data-option]').all()) {
					const id = await option.getAttribute('data-option');
					const item = items.find((i) => i.id === id)!;
					if ([item.gloss.en, (item.gloss as { id?: string }).id].includes(shown)) answer = id!;
				}
			}
			await ex.locator(`[data-option="${answer}"]`).click();
			await page.getByRole('button', { name: /^(Check|Cek)$/ }).click();
		}
		await page.getByRole('button', { name: /^(Continue|Lanjut)$/ }).click();
	}
	throw new Error('lesson did not finish');
}

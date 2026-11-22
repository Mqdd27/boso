import { expect, type Page } from '@playwright/test';
import pack from '../testdata/packs/ko-en/course.json' with { type: 'json' };
import { decompose } from '../src/lib/hangul.js';
import type { Course, Item } from '../src/lib/types.js';

export const course = pack as unknown as Course;
export const items = course.units.flatMap((u) => u.items);

/** A fake Korean voice and a fake <audio> player. Spoken text goes to window.__spoken, played
 *  files to window.__played ({src, rate}); a file that 404s rejects like a real broken file. */
export async function mockSpeech(page: Page) {
	await page.addInitScript(() => {
		type Played = { src: string; rate: number };
		const w = window as unknown as { __spoken: string[]; __played: Played[]; __heard: string[] };
		w.__spoken = [];
		w.__played = [];
		w.__heard = []; // item text or file src, in order
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
				speak: (u: Utterance) => {
					w.__spoken.push(u.text);
					w.__heard.push(u.text);
				},
				cancel: () => {},
				addEventListener: () => {}
			}
		});
		HTMLMediaElement.prototype.play = async function (this: HTMLMediaElement) {
			const res = await fetch(this.src);
			if (!res.ok) throw new DOMException('no file', 'NotSupportedError');
			const src = new URL(this.src).pathname;
			w.__played.push({ src, rate: this.playbackRate });
			w.__heard.push(src);
		};
		HTMLMediaElement.prototype.pause = () => {};
	});
}

/** Replay the sound and return the item it belongs to (autoplay may still be in flight). */
async function heard(page: Page): Promise<Item> {
	const log = () => page.evaluate(() => (window as never as { __heard: string[] }).__heard);
	const before = (await log()).length;
	await page.getByRole('button', { name: /Play again|Putar lagi/ }).click();
	await expect.poll(async () => (await log()).length).toBeGreaterThan(before);
	const src = (await log()).at(-1);
	return items.find((i) => i.text === src || src === `/packs/ko-en/audio/${i.audio}`)!;
}

/** On the home path: tap the unit's next lesson node (or a done one), then its Start/Practice. */
export async function openUnit(page: Page, id: string) {
	const unit = page.locator(`[data-unit="${id}"]`);
	const node = unit.locator('[data-node="active"], [data-node="done"]').first();
	await node.click();
	await expect(node).toHaveAttribute('aria-expanded', 'true');
	await unit.getByTestId('node-pop').getByRole('link').click();
}

/** Tap the tiles that make up `block` (각 = ㄱ + ㅏ + ㄱ) and wait for the live block to show it. */
export async function buildSyllable(page: Page, block: string) {
	const parts = decompose(block)!;
	for (const slot of ['initial', 'vowel', 'final'] as const) {
		if (parts[slot]) await page.locator(`[data-tile="${slot}:${parts[slot]}"]`).click();
	}
	await expect(page.getByTestId('block')).toHaveText(block);
}

const flat = (text: string) => text.replace(/\s+/g, '');

/** Tap the word-bank cards of `item` in order (with duplicates, any free copy will do). */
export async function arrange(page: Page, item: Item) {
	for (const token of item.tokens!) {
		await page.locator(`[data-card="${token}"]:not([disabled])`).first().click();
	}
	await expect(page.getByTestId('arranged')).toHaveText(new RegExp(item.tokens!.join('\\s*')));
}

/** The sentence an arrange exercise asks for: from its gloss, or by ear. */
export async function asked(page: Page): Promise<Item> {
	const ex = page.getByTestId('exercise');
	if ((await ex.getAttribute('data-listen')) === 'true') return heard(page);
	const shown = (await page.getByTestId('prompt').locator('p').first().innerText()).trim();
	return items.find((i) => i.type === 'sentence' && [i.gloss.en, i.gloss.id].includes(shown))!;
}

/** Answer every exercise of the current lesson correctly, until the end screen (or `steps`). */
export async function playLesson(page: Page, steps = 60) {
	const done = page.getByTestId('lesson-done');
	const ex = page.getByTestId('exercise');
	const check = page.getByRole('button', { name: /^(Check|Cek)$/ });
	let step = '';
	for (let n = 0; n < steps; n++) {
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
		} else if (kind === 'build') {
			// Shown as a sound (romanization) or played as audio.
			const sound = page.getByTestId('sound');
			const roman = (await sound.count()) ? (await sound.innerText()).trim() : null;
			const item = roman
				? items.find((i) => i.type === 'char' && i.roman === roman)!
				: await heard(page);
			await buildSyllable(page, item.text);
			await check.click();
		} else if (kind === 'arrange') {
			await arrange(page, await asked(page));
			await check.click();
		} else {
			await ex.locator(`[data-option="${await choiceAnswer(page)}"]`).click();
			await check.click();
		}
		await page.getByRole('button', { name: /^(Continue|Lanjut)$/ }).click();
	}
	if (steps === 60) throw new Error('lesson did not finish');
}

/** The id of the right option in a multiple-choice exercise (meaning, word, listen). */
export async function choiceAnswer(page: Page): Promise<string | undefined> {
	const ex = page.getByTestId('exercise');
	const prompt = page.getByTestId('prompt');
	const kind = await ex.getAttribute('data-kind');
	if (kind === 'meaning') {
		const text = flat(await prompt.locator('[lang="ko"]').first().innerText());
		return items.find((i) => flat(i.text) === text)?.id;
	}
	if (kind === 'listen') return (await heard(page)).id;
	// word: the prompt is a gloss (a sound in Hangul units); exactly one option has it
	const shown = (await prompt.locator('p').first().innerText()).trim();
	for (const option of await ex.locator('[data-option]').all()) {
		const id = await option.getAttribute('data-option');
		const item = items.find((i) => i.id === id)!;
		if ([item.gloss.en, item.gloss.id, item.roman].includes(shown)) return id!;
	}
}

/** Click through intro cards until a multiple-choice exercise shows. */
export async function skipToChoice(page: Page) {
	const ex = page.getByTestId('exercise');
	for (let n = 0; n < 20; n++) {
		await expect(ex).toBeVisible();
		if (await ex.locator('[data-option]').count()) return;
		await page.getByRole('button', { name: /^(Continue|Lanjut)$/ }).click();
	}
	throw new Error('no multiple-choice exercise');
}

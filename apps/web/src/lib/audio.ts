// Item audio: the pack's pre-generated .opus file, else the Web Speech API, else nothing.
import type { Item } from './types.js';

export type Source = 'file' | 'speech' | 'none';
export const SLOW = 0.7;

/** A voice for the course's language ('ko', 'zh'), or null if the device has none. */
export async function voiceFor(target: string): Promise<SpeechSynthesisVoice | null> {
	if (typeof speechSynthesis === 'undefined') return null;
	let voices = speechSynthesis.getVoices();
	if (!voices.length) {
		// Some browsers load voices asynchronously.
		await new Promise((resolve) => {
			speechSynthesis.addEventListener('voiceschanged', resolve, { once: true });
			setTimeout(resolve, 1000);
		});
		voices = speechSynthesis.getVoices();
	}
	return voices.find((v) => v.lang.replace('_', '-').toLowerCase().startsWith(target)) ?? null;
}

// A voice can't read pinyin script items (mā) right, only characters.
const speakable = (item: Item) => !/\p{Script=Latin}/u.test(item.text);

export const pickSource = (item: Item, voice: SpeechSynthesisVoice | null): Source =>
	item.audio ? 'file' : voice && speakable(item) ? 'speech' : 'none';

/** Listening exercises need a sound for every item of the unit. */
export const canListen = (items: Item[], voice: SpeechSynthesisVoice | null) =>
	items.every((i) => pickSource(i, voice) !== 'none');

let current: HTMLAudioElement | null = null;

/** Play an item. A missing or broken file falls back to speech; a blocked autoplay (iOS before
 *  the first tap) stays silent, the listen button still works afterwards. */
export async function play(
	item: Item,
	course: string,
	voice: SpeechSynthesisVoice | null,
	rate = 1
): Promise<Source> {
	current?.pause();
	if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel();
	if (item.audio) {
		const audio = new Audio(`/packs/${course}/audio/${item.audio}`);
		audio.playbackRate = rate;
		current = audio;
		try {
			await audio.play();
			return 'file';
		} catch (e) {
			if ((e as Error).name === 'NotAllowedError') return 'none';
		}
	}
	if (!voice || !speakable(item)) return 'none';
	const u = new SpeechSynthesisUtterance(item.text);
	u.voice = voice;
	u.lang = voice.lang;
	u.rate = 0.9 * rate;
	speechSynthesis.speak(u);
	return 'speech';
}

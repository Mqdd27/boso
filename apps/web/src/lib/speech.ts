// Web Speech API fallback until M3 ships audio files.

/** A Korean voice, or null if the device has none (then listening exercises are skipped). */
export async function koreanVoice(): Promise<SpeechSynthesisVoice | null> {
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
	return voices.find((v) => v.lang.replace('_', '-').toLowerCase().startsWith('ko')) ?? null;
}

export function speak(text: string, voice: SpeechSynthesisVoice) {
	speechSynthesis.cancel();
	const u = new SpeechSynthesisUtterance(text);
	u.voice = voice;
	u.lang = voice.lang;
	u.rate = 0.9;
	speechSynthesis.speak(u);
}

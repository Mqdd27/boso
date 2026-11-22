// Hangul jamo ↔ syllable blocks, by the Unicode formula (U+AC00), and letters that look or sound alike.
export const INITIALS = [...'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'];
export const VOWELS = [...'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'];
export const FINALS = ['', ...'ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'];

const BASE = 0xac00;

export type Parts = { initial: string; vowel: string; final: string };

/** (ㄱ, ㅏ, ㄱ) → 각; null if a part doesn't fit its slot. */
export function compose(initial: string, vowel: string, final = ''): string | null {
	const i = INITIALS.indexOf(initial);
	const v = VOWELS.indexOf(vowel);
	const f = FINALS.indexOf(final);
	if (i < 0 || v < 0 || f < 0) return null;
	return String.fromCharCode(BASE + (i * 21 + v) * 28 + f);
}

/** 각 → { initial: ㄱ, vowel: ㅏ, final: ㄱ }; null for anything that isn't one syllable block. */
export function decompose(text: string): Parts | null {
	const code = text.length === 1 ? text.charCodeAt(0) - BASE : -1;
	if (code < 0 || code >= 11172) return null;
	return {
		initial: INITIALS[Math.floor(code / 588)],
		vowel: VOWELS[Math.floor((code % 588) / 28)],
		final: FINALS[code % 28]
	};
}

// Letters learners mix up: the best wrong options.
const GROUPS = [
	'ㅓㅗㅜㅡ',
	'ㅏㅓㅑㅕ',
	'ㅗㅛㅜㅠ',
	'ㅐㅔㅒㅖ',
	'ㅘㅝㅚㅟㅙㅞ',
	'ㅢㅡㅣㅟ',
	'ㄱㅋㄲ',
	'ㄷㅌㄸ',
	'ㅂㅍㅃ',
	'ㅅㅆ',
	'ㅈㅊㅉ',
	'ㄴㄷㄹ',
	'ㅁㅂ',
	'ㅇㅎ'
].map((g) => [...g]);

export const confusable = (a: string, b: string) =>
	a !== b && GROUPS.some((g) => g.includes(a) && g.includes(b));

/** Letters, or syllables that differ from each other in one confusable letter (가/카, 각/갇). */
export function similar(a: string, b: string): boolean {
	const pa = decompose(a);
	const pb = decompose(b);
	if (!pa || !pb) return confusable(a, b);
	const diff = (['initial', 'vowel', 'final'] as const).filter((k) => pa[k] !== pb[k]);
	return diff.length === 1 && (confusable(pa[diff[0]], pb[diff[0]]) || diff[0] === 'final');
}
